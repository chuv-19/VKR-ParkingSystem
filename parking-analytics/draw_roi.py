import ctypes
import json
import subprocess
import sys
from pathlib import Path

import cv2

PROJECT_DIR = Path(__file__).resolve().parent
PARKING_JSON = PROJECT_DIR / "parking_spaces.json"
WINDOW_NAME = "ROI Selector"

current_polygon: list[tuple[int, int]] = []
all_polygons: list[list[tuple[int, int]]] = []


from video_paths import resolve_video_path


def resolve_requested_video() -> Path | None:
    if len(sys.argv) < 2:
        return resolve_video_path()

    requested = Path(sys.argv[1])
    if not requested.is_absolute():
        requested = PROJECT_DIR / requested
    return requested


def setup_display_window(frame_width: int, frame_height: int) -> None:
    """Окно с исходным соотношением сторон видео (без растягивания)."""
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.setWindowProperty(WINDOW_NAME, cv2.WND_PROP_ASPECT_RATIO, cv2.WINDOW_KEEPRATIO)

    try:
        screen_w = ctypes.windll.user32.GetSystemMetrics(0)
        screen_h = ctypes.windll.user32.GetSystemMetrics(1)
    except (AttributeError, OSError):
        screen_w, screen_h = 1920, 1080

    scale = min((screen_w * 0.9) / frame_width, (screen_h * 0.85) / frame_height, 1.0)
    disp_w = max(1, int(frame_width * scale))
    disp_h = max(1, int(frame_height * scale))
    cv2.resizeWindow(WINDOW_NAME, disp_w, disp_h)


def mouse_callback(event, x, y, flags, param):
    global current_polygon
    if event == cv2.EVENT_LBUTTONDOWN:
        current_polygon.append((x, y))
        print(f"Добавлена точка: ({x}, {y})")


def load_existing_polygons() -> None:
    global all_polygons
    if not PARKING_JSON.is_file():
        return
    with open(PARKING_JSON, encoding="utf-8") as f:
        all_polygons = json.load(f)
    print(f"Загружено {len(all_polygons)} существующих парковочных мест.")


def save_polygons() -> None:
    with open(PARKING_JSON, "w", encoding="utf-8") as f:
        json.dump(all_polygons, f, ensure_ascii=False)


def launch_monitoring() -> None:
    main_script = PROJECT_DIR / "main.py"
    if not main_script.is_file():
        print(f"Ошибка: не найден {main_script}")
        sys.exit(1)
    print("\nЗапуск мониторинга парковки...")
    result = subprocess.run([sys.executable, str(main_script)], cwd=PROJECT_DIR)
    sys.exit(result.returncode)


def main() -> None:
    global current_polygon

    video_path = resolve_requested_video()
    if video_path is None or not video_path.is_file():
        if len(sys.argv) >= 2:
            print(f"Ошибка: не найдено видео: {video_path}")
        else:
            print("Ошибка: не найдено видео в папке parking-analytics.")
            print("Положите .mp4 файл (например IMG_3220.mp4) в эту папку.")
        sys.exit(1)

    cap = cv2.VideoCapture(str(video_path))
    ret, frame = cap.read()
    cap.release()

    if not ret:
        print(f"Ошибка: не удалось прочитать первый кадр видео: {video_path}")
        sys.exit(1)

    load_existing_polygons()

    frame_h, frame_w = frame.shape[:2]
    setup_display_window(frame_w, frame_h)
    cv2.setMouseCallback(WINDOW_NAME, mouse_callback)
    print(f"Видео: {video_path.name}")
    print(f"Размер кадра: {frame_w}x{frame_h}")
    print("\nИнструкция:")
    print("1. Кликай ЛКМ, чтобы поставить 4 точки парковочного места.")
    print("2. Нажми 'S', чтобы сохранить текущее место и начать новое.")
    print("3. Нажми 'C', чтобы сбросить точки текущего (незавершенного) места.")
    print("4. Нажми 'Q', чтобы сохранить всё в JSON и запустить мониторинг.")

    while True:
        img_copy = frame.copy()

        for poly in all_polygons:
            for i in range(len(poly)):
                cv2.line(
                    img_copy,
                    tuple(poly[i]),
                    tuple(poly[(i + 1) % len(poly)]),
                    (0, 255, 0),
                    2,
                )

        if current_polygon:
            for i in range(len(current_polygon) - 1):
                cv2.line(img_copy, current_polygon[i], current_polygon[i + 1], (0, 0, 255), 2)
            for pt in current_polygon:
                cv2.circle(img_copy, pt, 4, (0, 0, 255), -1)

        cv2.imshow(WINDOW_NAME, img_copy)
        key = cv2.waitKey(1) & 0xFF

        if key in (ord("s"), ord("ы")):
            if len(current_polygon) >= 3:
                all_polygons.append(current_polygon)
                print(f"Паркоместо #{len(all_polygons)} успешно добавлено.")
                current_polygon = []
            else:
                print("Нужно поставить хотя бы 3 точки!")

        elif key in (ord("c"), ord("с")):
            current_polygon = []
            print("Текущие точки сброшены.")

        elif key in (ord("q"), ord("й")):
            save_polygons()
            print(f"Всего размечено мест: {len(all_polygons)}. Данные сохранены в {PARKING_JSON.name}")
            break

    cv2.destroyAllWindows()

    if not all_polygons:
        print("Ошибка: не размечено ни одного парковочного места.")
        sys.exit(1)

    launch_monitoring()


if __name__ == "__main__":
    main()
