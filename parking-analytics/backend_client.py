"""HTTP-клиент для связи CV-пайплайна с parking-backend."""
from __future__ import annotations

import os
import shutil
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

PROJECT_DIR = Path(__file__).resolve().parent
BACKEND_URL = os.getenv("PARKING_BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
UPLOADS_DIR = Path(os.getenv("PARKING_UPLOADS_DIR", str(PROJECT_DIR.parent / "parking-backend" / "uploads")))


def _post(path: str, params: dict) -> dict | None:
    query = urlencode(params)
    url = f"{BACKEND_URL}{path}?{query}"
    req = Request(url, method="POST")
    try:
        with urlopen(req, timeout=10) as resp:
            import json
            return json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        print(f"[backend_client] Ошибка POST {path}: {exc}")
        return None


def save_photo(crop_path: Path, plate_number: str, parking_slot: int) -> str | None:
    """Копирует фото в uploads backend и возвращает имя файла."""
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    safe_plate = "".join(ch for ch in plate_number.upper() if ch.isalnum())
    filename = f"{safe_plate}_slot{parking_slot}_{crop_path.stem}.jpg"
    dest = UPLOADS_DIR / filename
    try:
        shutil.copy2(crop_path, dest)
        return filename
    except Exception as exc:
        print(f"[backend_client] Не удалось сохранить фото: {exc}")
        return None


def report_entry(plate_number: str, parking_slot: int, photo_filename: str | None = None) -> dict | None:
    params = {
        "plate_number": plate_number,
        "parking_slot": str(parking_slot),
    }
    if photo_filename:
        params["photo_path"] = photo_filename
    result = _post("/parking/entry", params)
    if result:
        print(f"[backend_client] entry: {result.get('message', result)}")
    return result


def report_exit(plate_number: str) -> dict | None:
    result = _post("/parking/exit", {"plate_number": plate_number})
    if result:
        print(f"[backend_client] exit: {result.get('message', result)}")
    return result
