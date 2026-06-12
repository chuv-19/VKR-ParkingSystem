# macOS CLI запуск

В проект добавлен CLI для macOS:

```bash
./irs.sh help
```

Если после клонирования файл не исполняемый:

```bash
chmod +x ./irs.sh
```

## 1. Требования

Установите:

- Git
- Node.js LTS
- PostgreSQL
- Python 3.11+

`uv` CLI установится автоматически при `./irs.sh install`, если его нет.

Через Homebrew это обычно выглядит так:

```bash
brew install node postgresql@16
brew services start postgresql@16
```

## 2. Установка зависимостей

Из корня проекта:

```bash
./irs.sh install
```

Команда делает:

- проверяет Node/npm
- устанавливает `uv`, если его нет
- запускает `npm install` для `parking-api`
- запускает `npm install` для `parking-app`
- запускает `uv sync` для `parking-backend`
- запускает `uv sync --dev` для `parking-analytics`

На macOS Python-окружения создаются в `.venv-macos`, чтобы не конфликтовать с Windows `.venv`.

## 3. Инициализация базы данных

```bash
./irs.sh init-db
```

Команда ожидает локальный PostgreSQL на:

```text
localhost:5432
```

Она создает:

```text
role: postgres
password: 1234
database: parking_vkr
```

И затем запускает `parking-backend/database.py`, чтобы создать таблицы.

Если у PostgreSQL другой администратор или пароль:

```bash
./irs.sh init-db --db-admin-user "$(whoami)" --db-admin-password "your-password"
```

Windows-style параметры тоже поддерживаются:

```bash
./irs.sh init-db -DbAdminPassword "your-password"
```

## 4. Запуск web/backend стека

```bash
./irs.sh start
```

Перед запуском команда автоматически освобождает порты приложения:

- `8000` для backend
- `3001` для Express API
- `5173` для frontend

Сервисы запускаются в фоне, PID и логи лежат в `.irs-runtime/`.

Откройте:

```text
http://127.0.0.1:5173
```

Логи:

```bash
tail -f .irs-runtime/backend.log
tail -f .irs-runtime/frontend.log
```

## 5. Проверка статуса портов

```bash
./irs.sh status
```

## 6. Остановка web/backend стека

```bash
./irs.sh stop
```

Команда завершает процессы, которые слушают порты `8000`, `3001`, `5173`. PostgreSQL на `5432` она не трогает.

## 7. Разметка парковочных мест

Перед первым запуском аналитики нужно создать `parking-analytics/parking_spaces.json`.

```bash
./irs.sh roi IMG_3220.mp4
```

В окне разметки:

- клик ЛКМ добавляет точку
- `S` сохраняет текущее место
- `C` сбрасывает точки текущего места
- `Q` сохраняет JSON и запускает мониторинг

Видео должно лежать в:

```text
parking-analytics/
```

## 8. Запуск видеоаналитики

GUI-режим OpenCV:

```bash
./irs.sh analytics
```

Конкретное видео:

```bash
./irs.sh analytics IMG_3220.mp4
```

Видео должно лежать в:

```text
parking-analytics/
```

Headless-режим без OpenCV-окна:

```bash
./irs.sh headless IMG_3220.mp4
```

Ограничить количество кадров:

```bash
./irs.sh headless IMG_3220.mp4 --max-frames 300
```

Сделать фиксацию сразу после остановки в зоне:

```bash
./irs.sh headless IMG_3220.mp4 --zone-dwell-sec 0
```

Запустить без отправки в backend:

```bash
./irs.sh headless IMG_3220.mp4 --no-backend
```

## 9. Тесты ANPR

```bash
./irs.sh test
```

## 10. Типовой полный запуск

```bash
git clone <your-repo-url>
cd IRS_Parking_System

./irs.sh install
./irs.sh init-db
./irs.sh start
```

В другом терминале:

```bash
./irs.sh roi IMG_3220.mp4
./irs.sh analytics IMG_3220.mp4
```
