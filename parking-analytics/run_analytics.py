"""Точка входа CV-пайплайна: разметка зоны → мониторинг парковки."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent
PARKING_JSON = PROJECT_DIR / "parking_spaces.json"


def has_parking_layout() -> bool:
    if not PARKING_JSON.is_file():
        return False
    try:
        with open(PARKING_JSON, encoding="utf-8") as f:
            data = json.load(f)
        return isinstance(data, list) and len(data) > 0
    except (json.JSONDecodeError, OSError):
        return False


def run_script(name: str) -> int:
    script = PROJECT_DIR / name
    if not script.is_file():
        print(f"Ошибка: не найден {script}")
        return 1
    result = subprocess.run([sys.executable, str(script)], cwd=PROJECT_DIR)
    return result.returncode


def main() -> int:
    if has_parking_layout():
        print(f"Найдена разметка ({PARKING_JSON.name}), запуск мониторинга...")
        return run_script("main.py")

    print("Разметка парковочной зоны не найдена — открывается ROI Selector.")
    code = run_script("draw_roi.py")
    if code != 0:
        return code

    if not has_parking_layout():
        print("Ошибка: после разметки файл parking_spaces.json пуст или отсутствует.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
