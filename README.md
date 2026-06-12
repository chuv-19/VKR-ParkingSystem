# IRS Parking System

Система автоматизированной парковки: веб-приложение, backend с PostgreSQL и CV-аналитика.

Для Windows доступен CLI-скрипт автоматической установки и запуска: [WINDOWS_CLI.md](WINDOWS_CLI.md).

Для macOS доступен аналогичный CLI-скрипт: [MACOS_CLI.md](MACOS_CLI.md).

## Компоненты

| Папка | Назначение |
|-------|------------|
| `parking-app` | Vue 3 + TypeScript — сайт (карта, профиль, уведомления, история) |
| `parking-api` | Express — авторизация и прокси к parking-backend |
| `parking-backend` | FastAPI + PostgreSQL — сессии, уведомления, история, фото |
| `parking-analytics` | Python — детекция машин, распознавание ГРЗ, вызов backend |

## Локальный запуск

### 1. PostgreSQL

```powershell
cd parking-backend
# Запустите установленный PostgreSQL service или локальный PostgreSQL сервер.
```

### 2. Parking Backend (порт 8000)

```powershell
cd parking-backend
uv sync
uv run python database.py
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

### 3. Frontend + Auth API (порт 5173 + 3001)

```powershell
cd parking-app
npm install
npm run dev
```

Vite автоматически поднимает `parking-api` и проксирует `/api` и `/uploads`.

### 4. Аналитика (обработка видео)

```powershell
cd parking-analytics
uv sync --dev
# Положите видео (IMG_3115.mp4) и модель best.pt в папку
uv run python draw_roi.py   # если нет parking_spaces.json
uv run python main.py
```

При остановке машины в зоне парковки:
1. Распознаётся госномер (ANPR)
2. Фото сохраняется в `parking-backend/uploads/`
3. Вызывается `POST /parking/entry` — запускаются таймеры уведомлений (5 и 15 сек)
4. При выезде — `POST /parking/exit`

## Сценарий демонстрации

1. Зарегистрируйтесь на сайте (профиль)
2. Добавьте свой госномер в «Мой транспорт»
3. Запустите `uv run python main.py` с видео, где есть этот номер
4. Через ~5 сек в «Уведомлениях» появится предупреждение об оплате
5. Через ~15 сек — уведомление о штрафе
6. В «Истории парковок» появится запись с фотофиксацией

## Переменные окружения

**parking-api** (`.env`):
```
PORT=3001
PARKING_BACKEND_URL=http://127.0.0.1:8000
```

**parking-analytics**:
```
PARKING_BACKEND_URL=http://127.0.0.1:8000
PARKING_BACKEND_ENABLED=1
```
# parking-bullshit
