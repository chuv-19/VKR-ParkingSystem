"""Headless parking analytics runner for servers without OpenCV GUI."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import cv2

import main as analytics
from video_paths import resolve_video_path


PROJECT_DIR = Path(__file__).resolve().parent
PARKING_JSON = PROJECT_DIR / "parking_spaces.json"


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def main() -> int:
    analytics.ZONE_DWELL_SEC = _env_float("ZONE_DWELL_SEC", analytics.ZONE_DWELL_SEC)
    analytics.BACKEND_ENABLED = os.getenv("PARKING_BACKEND_ENABLED", "1") != "0"

    video_arg = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    video_path = video_arg if video_arg is not None else resolve_video_path()
    if video_path is None or not video_path.is_file():
        print("[analytics] No video file found in parking-analytics.", flush=True)
        return 1

    if not PARKING_JSON.is_file():
        print(f"[analytics] Missing {PARKING_JSON.name}. Create it with draw_roi.py first.", flush=True)
        return 1

    with open(PARKING_JSON, encoding="utf-8") as f:
        parking_places = json.load(f)
    if not parking_places:
        print(f"[analytics] {PARKING_JSON.name} has no parking zones.", flush=True)
        return 1

    model, model_name, vehicle_ids = analytics.load_model()
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        print(f"[analytics] Cannot open video: {video_path}", flush=True)
        return 1

    max_frames = _env_int("ANALYTICS_MAX_FRAMES", 0)
    log_every = max(1, _env_int("ANALYTICS_LOG_EVERY", 30))
    tracker = analytics.VehicleBoxTracker()
    places_state = {
        i: {
            "status": "FREE",
            "start_time": None,
            "empty_counter": 0,
            "vehicle_count": 0,
        }
        for i in range(len(parking_places))
    }

    print(
        f"[analytics] video={video_path.name} model={model_name} "
        f"zones={len(parking_places)} backend={analytics.BACKEND_ENABLED}",
        flush=True,
    )

    frame_index = 0
    started = time.time()
    while True:
        if max_frames and frame_index >= max_frames:
            print(f"[analytics] Stopped at ANALYTICS_MAX_FRAMES={max_frames}.", flush=True)
            break

        ok, frame = cap.read()
        if not ok:
            print("[analytics] Video ended.", flush=True)
            break

        results = model(frame, imgsz=640, conf=analytics.DETECT_CONF, verbose=False)[0]
        raw_detections: list[tuple[int, int, int, int, int]] = []
        for box in [] if results.boxes is None else results.boxes:
            cls = int(box.cls[0])
            if cls not in vehicle_ids:
                continue
            x1, y1, x2, y2 = map(int, box.xyxy[0])
            raw_detections.append((x1, y1, x2, y2, cls))

        stable_boxes = tracker.update(raw_detections, frame, parking_places)
        cars_in_zone = [0] * len(parking_places)
        for *_prefix, parking_idx in stable_boxes:
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
                    print(f"[analytics] Entry candidate: place={idx} vehicles={count}", flush=True)
                elif count != state["vehicle_count"]:
                    state["vehicle_count"] = count
            elif state["status"] == "OCCUPIED":
                state["empty_counter"] += 1
                if state["empty_counter"] > analytics.CONFIRMATION_FRAMES:
                    plate = analytics._slot_plates.pop(idx, None)
                    if plate and analytics.BACKEND_ENABLED:
                        from backend_client import report_exit

                        report_exit(plate)
                    print(f"[analytics] Exit candidate: place={idx} plate={plate}", flush=True)
                    state.update(
                        status="FREE",
                        start_time=None,
                        empty_counter=0,
                        vehicle_count=0,
                    )

        if frame_index % log_every == 0:
            print(
                f"[analytics] frame={frame_index} raw={len(raw_detections)} "
                f"stable={len(stable_boxes)} plates={analytics._slot_plates}",
                flush=True,
            )

        frame_index += 1

    cap.release()
    print(
        f"[analytics] Done. frames={frame_index} elapsed={time.time() - started:.1f}s "
        f"active_plates={analytics._slot_plates}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
