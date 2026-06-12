import os

os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

import ctypes
import sys
from pathlib import Path

import cv2
import time
import json
import numpy as np

PROJECT_DIR = Path(__file__).resolve().parent
PARKING_JSON = PROJECT_DIR / "parking_spaces.json"
MODEL_PATH = PROJECT_DIR / "yolov8n.pt"
DETECT_CONF = 0.25
VEHICLE_NAMES = frozenset({"car", "bus", "truck", "automobile"})
DISPLAY_WINDOW = "Parking Occupancy Monitoring"


def setup_display_window(window_name: str, frame_width: int, frame_height: int) -> None:
    """Окно с исходным соотношением сторон видео (без растягивания)."""
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(window_name, cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)
    if sys.platform == "win32" and hasattr(ctypes, "windll"):
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    else:
        screen_w = int(os.getenv("DISPLAY_WIDTH", "1440"))
        screen_h = int(os.getenv("DISPLAY_HEIGHT", "900"))
    scale = min((screen_w * 0.9) / frame_width, (screen_h * 0.85) / frame_height, 1.0)
    disp_w = max(1, int(frame_width * scale))
    disp_h = max(1, int(frame_height * scale))
    cv2.resizeWindow(window_name, disp_w, disp_h)


from video_paths import resolve_video_path


def resolve_requested_video() -> Path | None:
    if len(sys.argv) < 2:
        return resolve_video_path()

    requested = Path(sys.argv[1])
    if not requested.is_absolute():
        requested = PROJECT_DIR / requested
    return requested

try:
    from ultralytics import YOLO
except ModuleNotFoundError as e:
    if e.name == "ultralytics":
        print("Missing dependency: ultralytics")
        print("Install it with the SAME Python you run this script with:")
        print("  py -m pip install ultralytics")
        print("On Windows, if 'python' only prints 'Python', use: py main.py")
        raise
    raise


def require_file(path: Path, hint: str) -> None:
    if not path.is_file():
        print(f"Ошибка: не найден файл: {path}")
        print(hint)
        sys.exit(1)


def vehicle_class_ids(names: dict[int, str]) -> list[int]:
    ids = [i for i, name in names.items() if name.lower() in VEHICLE_NAMES]
    if ids:
        return ids
    if len(names) == 1:
        return [0]
    return [2, 5, 7]  # COCO: car, bus, truck


def load_model() -> tuple[YOLO, str, list[int]]:
    """Загружает yolov8n.pt (COCO: car, bus, truck)."""
    model_path = MODEL_PATH if MODEL_PATH.is_file() else "yolov8n.pt"
    model = YOLO(str(model_path))
    class_ids = vehicle_class_ids(model.names)
    model_name = model_path.name if isinstance(model_path, Path) else model_path
    return model, model_name, class_ids


CONFIRMATION_FRAMES = 30
# Стабилизация рамок детекции (debounce)
BOX_APPEAR_FRAMES = 3   # кадров подряд, чтобы рамка появилась
BOX_MISS_FRAMES = 20    # кадров без детекции, прежде чем рамка исчезнет
BOX_MATCH_IOU = 0.25    # порог совпадения рамок между кадрами
BOX_SMOOTH_ALPHA = 0.65  # доля предыдущей позиции (больше = плавнее)
# Детекция остановки ТС по рамке между кадрами
MOVE_CENTER_THRESHOLD = 2.5   # px смещения центра рамки за кадр
MOVE_PATCH_THRESHOLD = 4.0    # средняя разница яркости внутри рамки
STOP_CONFIRM_FRAMES = 18      # кадров подряд «без движения» → остановка
MOVE_CONFIRM_FRAMES = 4         # кадров движения, чтобы снова считать ТС едущим
ZONE_DWELL_SEC = 5.0            # секунд STOP в зоне до снимка, ANPR и отправки в backend
STOPPED_CROPS_DIR = PROJECT_DIR / "stopped_crops"
PLATE_MODEL_PATH = PROJECT_DIR / "best.pt"
BACKEND_ENABLED = os.getenv("PARKING_BACKEND_ENABLED", "1") != "0"

_anpr_processor = None
_slot_plates: dict[int, str] = {}
_slot_plate_ranks: dict[int, tuple] = {}


def get_anpr_processor():
    global _anpr_processor
    if _anpr_processor is not None:
        return _anpr_processor
    if not PLATE_MODEL_PATH.is_file():
        print(f"[ANPR] Модель {PLATE_MODEL_PATH.name} не найдена — распознавание номеров отключено.")
        return None
    try:
        from detector import ANPRProcessor
        print(f"[ANPR] Загрузка модели {PLATE_MODEL_PATH.name}...")
        _anpr_processor = ANPRProcessor(str(PLATE_MODEL_PATH))
        return _anpr_processor
    except Exception as exc:
        print(f"[ANPR] Не удалось загрузить распознавание номеров: {exc}")
        return None


def recognize_plate_from_crop(crop_path: Path) -> str | None:
    processor = get_anpr_processor()
    if processor is None:
        return None
    try:
        results = processor.process(str(crop_path))
        if not results:
            return None
        from detector import plate_result_rank

        best = max(
            results,
            key=lambda r: r.get("rank") or plate_result_rank(
                r,
                r.get("crop", np.empty((0, 0))).shape,
                getattr(processor, "known_plates", ()),
            ),
        )
        plate = best.get("plate_text", "").strip().upper()
        return plate if len(plate) >= 6 else None
    except Exception as exc:
        print(f"[ANPR] Ошибка распознавания {crop_path.name}: {exc}")
        return None


def recognize_plate_from_parking_region(
    frame: np.ndarray,
    polygon: list[tuple[int, int]] | list[list[int]],
) -> tuple[str, tuple] | None:
    processor = get_anpr_processor()
    if processor is None:
        return None
    try:
        from detector import detect_plate_boxes, post_process_ru_plate

        poly_np = np.array(polygon, dtype=np.int32)
        centroid = np.mean(poly_np.reshape(-1, 2), axis=0)
        box_distances: dict[tuple[int, int, int, int], float] = {}
        plate_boxes = []
        for box in detect_plate_boxes(processor.model, frame, conf=0.10):
            x1, y1, x2, y2 = box
            if x2 <= x1 or y2 <= y1:
                continue
            cx = (x1 + x2) // 2
            cy = (y1 + y2) // 2
            bottom_y = y2
            if (
                cv2.pointPolygonTest(poly_np, (cx, cy), False) >= 0
                or cv2.pointPolygonTest(poly_np, (cx, bottom_y), False) >= 0
            ):
                area = (x2 - x1) * (y2 - y1)
                distance = float(((cx - centroid[0]) ** 2 + (cy - centroid[1]) ** 2) ** 0.5)
                box_distances[box] = distance
                plate_boxes.append((box, distance, area))

        if not plate_boxes:
            return None

        plate_boxes.sort(key=lambda item: (item[1], -item[2]))
        candidate_boxes = [box for box, _bottom, _area in plate_boxes[:6]]
        results = processor.process_image_boxes(frame, candidate_boxes, margin=12)
        known = {post_process_ru_plate(p) for p in getattr(processor, "known_plates", ())}

        candidates = []
        for result in results:
            plate = post_process_ru_plate(result.get("plate_text", "")).strip().upper()
            if len(plate) >= 6 and (not known or plate in known):
                rank = result.get("rank", ())
                distance = box_distances.get(result.get("box"), 10**9)
                area = max(0, result["box"][2] - result["box"][0]) * max(0, result["box"][3] - result["box"][1])
                text_score = rank[0] if rank else 0
                candidates.append((text_score, -distance, area, plate, rank))
        if not candidates:
            return None
        candidates.sort(reverse=True)
        _text_score, _neg_distance, _area, plate, rank = candidates[0]
        return plate, rank
    except Exception as exc:
        print(f"[ANPR] Ошибка распознавания зоны парковки: {exc}")
        return None


def box_iou(a: tuple[int, int, int, int], b: tuple[int, int, int, int]) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    inter_x1, inter_y1 = max(ax1, bx1), max(ay1, by1)
    inter_x2, inter_y2 = min(ax2, bx2), min(ay2, by2)
    if inter_x2 <= inter_x1 or inter_y2 <= inter_y1:
        return 0.0
    inter = (inter_x2 - inter_x1) * (inter_y2 - inter_y1)
    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def smooth_box(
    old: tuple[int, int, int, int], new: tuple[int, int, int, int], alpha: float
) -> tuple[int, int, int, int]:
    return tuple(int(alpha * o + (1 - alpha) * n) for o, n in zip(old, new))


def box_center(box: tuple[int, int, int, int]) -> tuple[int, int]:
    x1, y1, x2, y2 = box
    return (x1 + x2) // 2, (y1 + y2) // 2


def clamp_box(
    box: tuple[int, int, int, int], width: int, height: int
) -> tuple[int, int, int, int]:
    x1, y1, x2, y2 = box
    x1 = max(0, min(x1, width - 1))
    y1 = max(0, min(y1, height - 1))
    x2 = max(x1 + 1, min(x2, width))
    y2 = max(y1 + 1, min(y2, height))
    return x1, y1, x2, y2


def crop_box(frame: np.ndarray, box: tuple[int, int, int, int]) -> np.ndarray:
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = clamp_box(box, w, h)
    return frame[y1:y2, x1:x2].copy()


def patch_mean_diff(
    frame: np.ndarray,
    prev_frame: np.ndarray,
    box: tuple[int, int, int, int],
) -> float:
    """Средняя разница яркости внутри рамки между двумя кадрами."""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = clamp_box(box, w, h)
    cur = cv2.cvtColor(frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    prev = cv2.cvtColor(prev_frame[y1:y2, x1:x2], cv2.COLOR_BGR2GRAY)
    if cur.size == 0 or prev.size == 0 or cur.shape != prev.shape:
        return float("inf")
    return float(np.mean(cv2.absdiff(cur, prev)))


def vehicle_parking_place(
    box: tuple[int, int, int, int],
    parking_places: list[list[tuple[int, int]]],
) -> int | None:
    """ТС считается в зоне, если нижний центр и геом. центр рамки внутри полигона."""
    x1, y1, x2, y2 = box
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    bottom_y = y2 - max(1, (y2 - y1) // 12)
    anchors = ((cx, bottom_y), (cx, cy))

    for idx, polygon in enumerate(parking_places):
        poly_np = np.array(polygon, dtype=np.int32)
        if all(cv2.pointPolygonTest(poly_np, pt, False) >= 0 for pt in anchors):
            return idx
    return None


def on_vehicle_stopped(
    crop: np.ndarray,
    frame: np.ndarray,
    track_id: int,
    box: tuple[int, int, int, int],
    parking_place: int,
    parking_polygon: list[tuple[int, int]] | list[list[int]],
) -> None:
    """Снимок, ANPR и въезд в backend после ZONE_DWELL_SEC стояния в зоне."""
    STOPPED_CROPS_DIR.mkdir(exist_ok=True)
    filename = STOPPED_CROPS_DIR / f"vehicle_{track_id}_place{parking_place}.jpg"
    cv2.imwrite(str(filename), crop)
    print(
        f" [ФИКСАЦИЯ] ТС #{track_id}, место #{parking_place} "
        f"({ZONE_DWELL_SEC:.0f} сек в зоне): снимок {filename.name} "
        f"({crop.shape[1]}x{crop.shape[0]})"
    )

    rank = (-1000,)
    region_result = recognize_plate_from_parking_region(frame, parking_polygon)
    if region_result:
        plate, rank = region_result
        print(f" [ANPR] Распознан номер по зоне парковки: {plate}")
    else:
        plate = recognize_plate_from_crop(filename)
        rank = (0, len(plate or ""))
    if not plate:
        print(f" [ANPR] Номер не распознан для ТС #{track_id} на месте #{parking_place}")
        return

    current_plate = _slot_plates.get(parking_place)
    current_rank = _slot_plate_ranks.get(parking_place, (-1000,))
    if current_plate:
        if plate != current_plate and rank > current_rank:
            print(f" [ANPR] Уточнение места #{parking_place}: {current_plate} → {plate}")
            _slot_plates[parking_place] = plate
            _slot_plate_ranks[parking_place] = rank
            if BACKEND_ENABLED:
                from backend_client import report_entry, report_exit, save_photo

                report_exit(current_plate)
                photo_filename = save_photo(filename, plate, parking_place)
                report_entry(plate, parking_place, photo_filename)
        return

    print(f" [ANPR] Распознан номер: {plate}")
    _slot_plates[parking_place] = plate
    _slot_plate_ranks[parking_place] = rank

    if not BACKEND_ENABLED:
        return

    from backend_client import report_entry, save_photo

    photo_filename = save_photo(filename, plate, parking_place)
    report_entry(plate, parking_place, photo_filename)


class VehicleBoxTracker:
    """Держит рамки стабильными и определяет, движется ли ТС между кадрами."""

    def __init__(self) -> None:
        self._tracks: dict[int, dict] = {}
        self._next_id = 0
        self._prev_frame: np.ndarray | None = None

    def _new_track(self, det_box: tuple[int, int, int, int], cls: int) -> dict:
        return {
            "box": det_box,
            "cls": cls,
            "miss": 0,
            "hits": 1,
            "confirmed": BOX_APPEAR_FRAMES <= 1,
            "prev_center": None,
            "still_frames": 0,
            "move_frames": 0,
            "is_moving": True,
            "zone_still_since": None,
            "entry_reported": False,
        }

    def _update_motion(self, track: dict, frame: np.ndarray) -> None:
        box = track["box"]
        center = box_center(box)
        center_shift = 0.0
        if track["prev_center"] is not None:
            px, py = track["prev_center"]
            cx, cy = center
            center_shift = ((cx - px) ** 2 + (cy - py) ** 2) ** 0.5

        patch_shift = 0.0
        if self._prev_frame is not None:
            patch_shift = patch_mean_diff(frame, self._prev_frame, box)

        is_frame_moving = (
            center_shift > MOVE_CENTER_THRESHOLD
            or patch_shift > MOVE_PATCH_THRESHOLD
        )

        if is_frame_moving:
            track["move_frames"] += 1
            track["still_frames"] = 0
            if track["move_frames"] >= MOVE_CONFIRM_FRAMES:
                track["is_moving"] = True
                track["zone_still_since"] = None
        else:
            track["still_frames"] += 1
            track["move_frames"] = 0
            if track["still_frames"] >= STOP_CONFIRM_FRAMES:
                track["is_moving"] = False

        track["prev_center"] = center

    def update(
        self,
        detections: list[tuple[int, int, int, int, int]],
        frame: np.ndarray,
        parking_places: list[list[tuple[int, int]]],
    ) -> list[tuple[int, int, int, int, int, int, bool, int | None]]:
        matched_track_ids: set[int] = set()

        for det in detections:
            det_box = det[:4]
            best_id, best_iou = None, BOX_MATCH_IOU
            for tid, track in self._tracks.items():
                if tid in matched_track_ids:
                    continue
                iou = box_iou(det_box, track["box"])
                if iou > best_iou:
                    best_iou, best_id = iou, tid

            if best_id is not None:
                track = self._tracks[best_id]
                track["box"] = smooth_box(track["box"], det_box, BOX_SMOOTH_ALPHA)
                track["cls"] = det[4]
                track["miss"] = 0
                track["hits"] += 1
                if track["hits"] >= BOX_APPEAR_FRAMES:
                    track["confirmed"] = True
                matched_track_ids.add(best_id)
            else:
                self._next_id += 1
                self._tracks[self._next_id] = self._new_track(det_box, det[4])
                matched_track_ids.add(self._next_id)

        for tid, track in list(self._tracks.items()):
            if tid in matched_track_ids:
                continue
            track["miss"] += 1
            if track["miss"] > BOX_MISS_FRAMES:
                del self._tracks[tid]

        visible: list[tuple[int, int, int, int, int, int, bool, int | None]] = []
        for tid, track in self._tracks.items():
            if not track["confirmed"] or track["miss"] > BOX_MISS_FRAMES:
                continue
            self._update_motion(track, frame)

            parking_place = vehicle_parking_place(track["box"], parking_places)
            is_parked = not track["is_moving"] and parking_place is not None
            visible.append((*track["box"], track["cls"], tid, is_parked, parking_place))

            if track["is_moving"] or parking_place is None:
                track["zone_still_since"] = None
            elif track["zone_still_since"] is None:
                track["zone_still_since"] = time.time()
            elif (
                not track["entry_reported"]
                and time.time() - track["zone_still_since"] >= ZONE_DWELL_SEC
            ):
                crop = crop_box(frame, track["box"])
                on_vehicle_stopped(
                    crop,
                    frame,
                    tid,
                    track["box"],
                    parking_place,
                    parking_places[parking_place],
                )
                if parking_place in _slot_plates:
                    track["entry_reported"] = True
                else:
                    track["zone_still_since"] = time.time()

        self._prev_frame = frame.copy()
        return visible


def main() -> None:
    video_path = resolve_requested_video()
    if video_path is None:
        print("Ошибка: не найдено видео в папке parking-analytics.")
        print("Положите .mp4 файл (например IMG_3220.mp4) в эту папку.")
        sys.exit(1)
    require_file(video_path, "Видеофайл повреждён или недоступен для чтения.")

    if not PARKING_JSON.is_file():
        print(f"Ошибка: не найден {PARKING_JSON}")
        print(f"Сначала создайте разметку: ./irs.sh roi {video_path.name}")
        sys.exit(1)

    with open(PARKING_JSON, "r", encoding="utf-8") as f:
        parking_places = json.load(f)

    if not parking_places:
        print(f"Ошибка: в {PARKING_JSON} нет парковочных мест.")
        print(f"Запустите разметку: ./irs.sh roi {video_path.name} (S — сохранить место, Q — выйти)")
        sys.exit(1)

    print(f"Успешно загружено мест для контроля: {len(parking_places)}")
    print(f"Видео: {video_path.name}")

    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"Ошибка: не удалось открыть видео: {video_path}")
        sys.exit(1)

    ret, probe_frame = cap.read()
    if not ret:
        print("Ошибка: не удалось прочитать первый кадр видео.")
        cap.release()
        sys.exit(1)

    model, model_name, vehicle_ids = load_model()
    id_labels = ", ".join(f"{i}={model.names[i]}" for i in vehicle_ids)
    print(f"Модель: {model_name} (классы ТС: {id_labels})")

    places_state = {
        i: {
            "status": "FREE",
            "start_time": None,
            "empty_counter": 0,
            "vehicle_count": 0,
        }
        for i in range(len(parking_places))
    }

    frame_h, frame_w = probe_frame.shape[:2]
    setup_display_window(DISPLAY_WINDOW, frame_w, frame_h)
    print("Окно открыто. Нажмите Q в окне видео для выхода.")
    frame = probe_frame
    box_tracker = VehicleBoxTracker()

    while True:
        results = model(frame, imgsz=640, conf=DETECT_CONF, verbose=False)[0]
        boxes = [] if results.boxes is None else results.boxes

        raw_detections: list[tuple[int, int, int, int, int]] = []
        for box in boxes:
            cls = int(box.cls[0])
            if cls not in vehicle_ids:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            raw_detections.append((x1, y1, x2, y2, cls))

        stable_boxes = box_tracker.update(raw_detections, frame, parking_places)
        cars_in_zone = [0] * len(parking_places)

        for x1, y1, x2, y2, cls, track_id, is_parked, parking_idx in stable_boxes:
            cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
            box_color = (0, 255, 255) if is_parked else (255, 0, 0)
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)
            cv2.circle(frame, (cx, cy), 5, box_color, -1)
            motion_label = "STOP" if is_parked else "MOVE"
            cv2.putText(
                frame, f"#{track_id} {motion_label}", (x1, max(y1 - 8, 12)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, box_color, 1,
            )

            if parking_idx is not None:
                cars_in_zone[parking_idx] += 1

        for idx, count in enumerate(cars_in_zone):
            state = places_state[idx]
            if count > 0:
                state["empty_counter"] = 0
                if state["status"] == "FREE":
                    state["status"] = "OCCUPIED"
                    state["start_time"] = time.time()
                    state["vehicle_count"] = count
                    print(f" [ВЪЕЗД] Место #{idx} занято: {count} ТС в зоне")
                elif count != state["vehicle_count"]:
                    print(
                        f" [ИЗМЕНЕНИЕ] Место #{idx}: "
                        f"{state['vehicle_count']} → {count} ТС в зоне"
                    )
                    state["vehicle_count"] = count
            elif state["status"] == "OCCUPIED":
                state["empty_counter"] += 1
                if state["empty_counter"] > CONFIRMATION_FRAMES:
                    duration = time.time() - state["start_time"]
                    was = state["vehicle_count"]
                    print(
                        f" [ВЫЕЗД] Место #{idx} свободно "
                        f"(было {was} ТС). Стоянка: {int(duration)} сек."
                    )
                    plate = _slot_plates.pop(idx, None)
                    _slot_plate_ranks.pop(idx, None)
                    if plate and BACKEND_ENABLED:
                        from backend_client import report_exit
                        report_exit(plate)
                    places_state[idx] = {
                        "status": "FREE",
                        "start_time": None,
                        "empty_counter": 0,
                        "vehicle_count": 0,
                    }

        for idx, polygon in enumerate(parking_places):
            poly_np = np.array(polygon, dtype=np.int32)
            state = places_state[idx]
            if state["status"] == "OCCUPIED":
                color = (0, 0, 255)
                n = state["vehicle_count"]
                status_text = f"OCCUPIED ({n} TC)"
            else:
                color, status_text = (0, 255, 0), "FREE"
            cv2.polylines(frame, [poly_np], True, color, 2)
            label_pos = tuple(polygon[0])
            cv2.putText(
                frame, f"P{idx}: {status_text}", (label_pos[0], label_pos[1] - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2,
            )

        cv2.imshow(DISPLAY_WINDOW, frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

        ret, frame = cap.read()
        if not ret:
            print("Видео завершено.")
            break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
