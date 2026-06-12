# Полная инструкция по запуску IRS Parking System

Ниже описан полный путь от клонирования репозитория до запуска backend, frontend, API и видеоаналитики.

Для Windows доступен CLI-скрипт автоматической установки и запуска: [WINDOWS_CLI.md](WINDOWS_CLI.md).

## 1. Предварительные требования

Установите:

```bash
# macOS через Homebrew
brew install git node uv
```

Если Homebrew не установлен, `uv` можно поставить так:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Также нужен PostgreSQL. Установите PostgreSQL для Windows и убедитесь, что сервер запущен.

Проверьте инструменты:

```bash
git --version
node --version
npm --version
uv --version
```

## 2. Клонирование проекта

```bash
git clone <your-repo-url>
cd IRS_Parking_System
```

Замените `<your-repo-url>` на реальный URL GitHub-репозитория.

## 3. Запуск PostgreSQL

Запустите установленный PostgreSQL service или локальный PostgreSQL сервер.

Если локальный PostgreSQL уже запущен, создайте ожидаемые роль и базу данных:

```bash
psql -h localhost -p 5432 -d postgres <<'SQL'
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'postgres') THEN
    CREATE ROLE postgres WITH LOGIN SUPERUSER PASSWORD '1234';
  ELSE
    ALTER ROLE postgres WITH LOGIN SUPERUSER PASSWORD '1234';
  END IF;
END $$;

SELECT 'CREATE DATABASE parking_vkr OWNER postgres'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'parking_vkr')\gexec
SQL
```

## 4. Запуск Parking Backend

В папке `parking-backend`:

```bash
uv sync
uv run python database.py
uv run uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Проверка в другом терминале:

```bash
curl http://127.0.0.1:8000/health
```

Ожидаемый ответ:

```json
{"ok":true,"service":"parking-backend"}
```

## 5. Запуск Frontend и Express API

В новом терминале:

```bash
cd IRS_Parking_System/parking-app
npm install
npm run dev -- --host 127.0.0.1
```

Будут запущены:

```text
Frontend: http://127.0.0.1:5173
Express API: http://127.0.0.1:3001
```

Проверка:

```bash
curl http://127.0.0.1:3001/api/health
curl http://127.0.0.1:5173/api/health
```

Откройте в браузере:

```text
http://127.0.0.1:5173
```

## 6. Подготовка видеоаналитики

В новом терминале:

```bash
cd IRS_Parking_System/parking-analytics
uv sync --dev
```

Убедитесь, что в папке `parking-analytics` есть файлы:

```text
best.pt
yolov8n.pt
parking_spaces.json
```

При необходимости скопируйте видео:

```bash
cp /Users/daniil/Downloads/IMG_3220.mp4 ./IMG_3220.mp4
cp /Users/daniil/Downloads/IMG_3217.mp4 ./IMG_3217.mp4
cp /Users/daniil/Downloads/IMG_3498.mp4 ./IMG_3498.mp4
```

## 7. Запуск видеоаналитики

Обычный запуск с GUI-окном OpenCV:

```bash
cd IRS_Parking_System/parking-analytics
PARKING_BACKEND_URL=http://127.0.0.1:8000 \
PARKING_BACKEND_ENABLED=1 \
uv run python main.py
```

Если файла `parking_spaces.json` нет, сначала создайте разметку:

```bash
uv run python draw_roi.py
```

Управление в окне разметки:

```text
S = сохранить текущую парковочную зону
C = сбросить текущие точки
Q = сохранить разметку и запустить мониторинг
```

## 8. Запуск unit-тестов ANPR

```bash
cd IRS_Parking_System/parking-analytics
UV_PROJECT_ENVIRONMENT=.venv-macos uv run pytest -q
```

Ожидаемый текущий результат:

```text
7 passed
```

На обычной свежей установке также можно использовать:

```bash
uv run pytest -q
```

## 9. Регистрация тестового пользователя и номера

Можно использовать frontend UI или выполнить запросы напрямую:

```bash
curl -X POST "http://127.0.0.1:8000/users/sync?full_name=Video%20Test&email=video-test@example.local&api_user_id=video-test"

curl -X POST "http://127.0.0.1:8000/vehicles/add?user_id=1&plate_number=P221EM178&model=VideoTest"
```

## 10. Проверка результатов

История парковок:

```bash
curl "http://127.0.0.1:8000/parking/history?user_id=1"
```

Уведомления:

```bash
curl "http://127.0.0.1:8000/notifications?user_id=1"
```

Загруженные фото сохраняются здесь:

```text
parking-backend/uploads/
```

Кропы автомобилей из аналитики сохраняются здесь:

```text
parking-analytics/stopped_crops/
```

## 11. Частые проблемы

Если Vite пишет `Permission denied`:

```bash
cd parking-app
chmod +x node_modules/.bin/* ../parking-api/node_modules/.bin/* 2>/dev/null || true
npm install
npm run dev -- --host 127.0.0.1
```

Если backend пишет, что роль `postgres` не существует, выполните блок создания роли и базы данных из раздела 3.

Если аналитика не находит видео, положите `.mp4` файл прямо в папку:

```text
parking-analytics/
```

Предпочтительные имена видео:

```text
IMG_3220.mp4
IMG_3498.mp4
IMG_3115.mp4
parking.mp4
```
