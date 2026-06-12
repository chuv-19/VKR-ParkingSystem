"""Поиск видеофайла в папке parking-analytics."""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent

PREFERRED_VIDEO_NAMES = (
    "IMG_3220.mp4",
    "IMG_3498.mp4",
    "IMG_3115.mp4",
    "parking.mp4",
)


def resolve_video_path() -> Path | None:
    by_name = {p.name.lower(): p for p in PROJECT_DIR.iterdir() if p.is_file()}

    for name in PREFERRED_VIDEO_NAMES:
        path = by_name.get(name.lower())
        if path is not None:
            return path

    mp4_files = sorted(
        (p for p in PROJECT_DIR.iterdir() if p.is_file() and p.suffix.lower() == ".mp4"),
        key=lambda p: p.name.lower(),
    )
    return mp4_files[0] if mp4_files else None
