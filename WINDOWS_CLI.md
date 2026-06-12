# Windows CLI запуск

В проект добавлен CLI для Windows:

```powershell
.\irs.cmd help
```

Он оборачивает PowerShell-скрипт `irs.ps1` и запускает его с `ExecutionPolicy Bypass` только для этой команды.

## 1. Требования

Установите:

- Git
- Node.js LTS
- PostgreSQL for Windows
- Python 3.11+

`uv` CLI установится автоматически при `.\irs.cmd install`, если его нет.

Проверьте, что PostgreSQL service запущен. Обычно он виден в Windows Services как `postgresql-x64-*`.

## 2. Установка зависимостей

Из корня проекта:

```powershell
.\irs.cmd install
```

Команда делает:

- проверяет Node/npm
- устанавливает `uv`, если его нет
- запускает `npm install` для `parking-api`
- запускает `npm install` для `parking-app`
- запускает `uv sync` для `parking-backend`
- запускает `uv sync --dev` для `parking-analytics`

## 3. Инициализация базы данных

```powershell
.\irs.cmd init-db
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

Если при установке PostgreSQL вы задавали другой пароль для пользователя `postgres`, передайте его так:

```powershell
.\irs.cmd init-db -DbAdminPassword "your-postgres-password"
```

После успешной инициализации скрипт выставит пароль роли `postgres` в `1234`, потому что именно это значение ожидает backend по умолчанию.

## 4. Запуск web/backend стека

```powershell
.\irs.cmd start
```

Перед запуском команда автоматически освобождает порты приложения:

- `8000` для backend
- `3001` для Express API
- `5173` для frontend

Если на этих портах остались старые процессы Node/Vite/Uvicorn, скрипт завершит их через Windows API `Get-NetTCPConnection` + `Stop-Process`.

Откроются отдельные PowerShell-окна:

- backend на `http://127.0.0.1:8000`
- frontend на `http://127.0.0.1:5173`
- Express API на `http://127.0.0.1:3001`

Откройте:

```text
http://127.0.0.1:5173
```

## 5. Проверка статуса портов

```powershell
.\irs.cmd status
```

## 6. Остановка web/backend стека

```powershell
.\irs.cmd stop
```

Команда завершает процессы, которые слушают порты `8000`, `3001`, `5173`. PostgreSQL на `5432` она не трогает.

## 7. Запуск видеоаналитики

GUI-режим OpenCV:

```powershell
.\irs.cmd analytics
```

Конкретное видео:

```powershell
.\irs.cmd analytics IMG_3220.mp4
```

Видео должно лежать в:

```text
parking-analytics\
```

Headless-режим без OpenCV-окна:

```powershell
.\irs.cmd headless IMG_3220.mp4
```

Ограничить количество кадров:

```powershell
.\irs.cmd headless IMG_3220.mp4 -MaxFrames 300
```

Сделать фиксацию сразу после остановки в зоне:

```powershell
.\irs.cmd headless IMG_3220.mp4 -ZoneDwellSec 0
```

Запустить без отправки в backend:

```powershell
.\irs.cmd headless IMG_3220.mp4 -NoBackend
```

## 8. Тесты ANPR

```powershell
.\irs.cmd test
```

## 9. Типовой полный запуск

```powershell
git clone <your-repo-url>
cd IRS_Parking_System

.\irs.cmd install
.\irs.cmd init-db
.\irs.cmd start
```

В другом терминале:

```powershell
.\irs.cmd analytics IMG_3220.mp4
```

## 10. Частые проблемы

Если `psql` не найден:

Добавьте PostgreSQL `bin` в PATH, например:

```text
C:\Program Files\PostgreSQL\16\bin
```

Если `uv` установился, но команда все еще не найдена:

Откройте новый терминал и повторите команду.

Если frontend не запускается:

```powershell
cd parking-app
npm install
cd ..
.\irs.cmd start
```

Если backend пишет, что роль `postgres` или база `parking_vkr` не существует:

```powershell
.\irs.cmd init-db
```

Если появляется ошибка `EADDRINUSE` для `127.0.0.1:3001`, значит старый API-процесс еще слушает порт. Запустите:

```powershell
.\irs.cmd stop
.\irs.cmd start
```
