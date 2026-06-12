import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import asyncio

import database

UPLOADS_DIR = Path(__file__).resolve().parent / "uploads"
UPLOADS_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        database.init_db()
    except Exception as exc:
        print(f"[WARN] Не удалось инициализировать БД при старте: {exc}")
        print("Убедитесь, что PostgreSQL service запущен.")
    yield


app = FastAPI(
    title="Intelligent Road System (IRS) - Parking API",
    description="API для управления автоматизированной парковкой",
    version="1.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173", "http://127.0.0.1:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory=str(UPLOADS_DIR)), name="uploads")


async def schedule_parking_alerts(plate_number: str, user_id: int):
    # Въезд в backend уже после 5 сек стояния в зоне — первое уведомление сразу.
    session = database.get_active_session(plate_number)
    if session and not session[4]:
        msg = (
            f"Автомобиль {plate_number} зафиксирован на платной парковке. "
            "Пожалуйста, оплатите сессию."
        )
        database.add_notification(user_id, plate_number, msg, level="warning")

    # Ещё 10 сек → 15 сек от начала стояния в зоне.
    await asyncio.sleep(10)

    session = database.get_active_session(plate_number)
    if session and not session[4]:
        msg = (
            f"Время бесплатного ожидания истекло! Автомобиль {plate_number} "
            "не оплатил парковку. Направлен запрос в ГИБДД — возможен штраф."
        )
        database.add_notification(user_id, plate_number, msg, level="critical")


@app.get("/")
def read_root():
    return {"message": "API системы управления парковкой работает успешно!", "ok": True}


@app.get("/health")
def health():
    return {"ok": True, "service": "parking-backend"}


@app.post("/users/sync")
def sync_user(full_name: str, email: str, api_user_id: str | None = None):
    user_id = database.sync_user(full_name, email, api_user_id)
    return {"status": "success", "user_id": user_id}


@app.post("/users/register")
def register_user(full_name: str, email: str, balance: float = 0.0):
    user_id = database.add_user(full_name, email, balance)
    if user_id is None:
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    return {"status": "success", "user_id": user_id}


@app.post("/vehicles/add")
def add_user_vehicle(user_id: int, plate_number: str, model: str = ""):
    vehicle_id = database.add_vehicle(user_id, plate_number, model)
    if vehicle_id is None:
        raise HTTPException(status_code=400, detail="Автомобиль с таким номером уже зарегистрирован")
    return {"status": "success", "vehicle_id": vehicle_id}


@app.get("/vehicles/list")
def list_user_vehicles(user_id: int):
    rows = database.list_vehicles(user_id)
    return {
        "vehicles": [
            {"id": row[0], "plate_number": row[1], "model": row[2] or ""}
            for row in rows
        ]
    }


@app.post("/parking/entry")
def vehicle_entry(
    plate_number: str,
    parking_slot: int,
    background_tasks: BackgroundTasks,
    photo_path: str | None = None,
):
    plate = plate_number.strip().upper()
    if not plate:
        raise HTTPException(status_code=400, detail="Номер не распознан")

    active = database.get_active_session(plate)
    if active:
        return {
            "status": "skipped",
            "session_id": active[0],
            "message": f"Сессия для {plate} уже активна",
        }

    vehicle_info = database.check_vehicle_exists(plate)
    session_id = database.start_parking_session(plate, parking_slot, photo_path=photo_path)

    if vehicle_info:
        _vehicle_id, user_id = vehicle_info
        background_tasks.add_task(schedule_parking_alerts, plate, user_id)
        msg = f"Въезд {plate} зафиксирован. Владелец найден, таймеры уведомлений запущены."
    else:
        msg = f"Въезд {plate} зафиксирован (гостевой визит)."

    return {"status": "success", "session_id": session_id, "message": msg}


@app.post("/parking/exit")
def vehicle_exit(plate_number: str):
    plate = plate_number.strip().upper()
    session_id = database.end_parking_session(plate)
    if session_id is None:
        raise HTTPException(status_code=404, detail="Активная сессия не найдена")
    return {"status": "success", "session_id": session_id, "message": f"Выезд {plate} зафиксирован"}


@app.get("/notifications")
def get_notifications(user_id: int, limit: int = 50):
    rows = database.get_notifications(user_id, limit)
    return {
        "notifications": [
            {
                "id": row[0],
                "plate_number": row[1],
                "message": row[2],
                "level": row[3],
                "created_at": row[4].isoformat(),
                "is_read": bool(row[5]),
            }
            for row in rows
        ]
    }


@app.get("/parking/history")
def parking_history(user_id: int, limit: int = 50):
    rows = database.get_parking_history(user_id, limit)
    return {
        "history": [
            {
                "id": str(row[0]),
                "vehicle": row[1],
                "address": database.PARKING_ADDRESS,
                "started_at": row[2].strftime("%d.%m.%Y %H:%M"),
                "ended_at": row[3].strftime("%d.%m.%Y %H:%M") if row[3] else "—",
                "photo_url": (
                    f"/uploads/{Path(row[4]).name}"
                    if row[4] and not str(row[4]).startswith(("http", "/"))
                    else (row[4] or "")
                ),
                "parking_slot": row[5],
            }
            for row in rows
        ]
    }
