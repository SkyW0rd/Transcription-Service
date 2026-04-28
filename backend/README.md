# Transcription Web App Backend

## Stack

- FastAPI
- Python
- SQLAlchemy
- SQLite
- Background worker thread
- FFmpeg
- Whisper
- ReportLab
- REST API

## Responsibilities

Backend отвечает за обработку аудио и предоставление API для frontend:

- приём аудиофайлов
- создание и хранение задач обработки (jobs)
- сохранение файлов в локальное хранилище
- нормализация аудио через FFmpeg
- транскрибация через Whisper
- формирование summary
- генерация PDF отчёта
- выдача статусов обработки
- отдача transcript, summary и PDF через API

Все данные хранятся локально: SQLite база, исходные аудиофайлы и PDF отчёты.

## Run locally

```bash
cd backend
python -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend будет доступен по адресу:
`http://localhost:8000`

Swagger UI:
`http://localhost:8000/docs`

Health check:
`http://localhost:8000/health`

---

## Project structure

```text
backend/
  app/
    api/
      routes/          # API endpoints
    core/              # config and logging
    models/            # SQLAlchemy models
    repositories/      # database access layer
    schemas/           # Pydantic schemas
    services/          # ffmpeg / whisper / summary / pdf / worker
    db.py              # database connection
    main.py            # FastAPI application entrypoint
  Dockerfile
  requirements.txt
  ```

---

## API endpoints

- `GET /health`
- `POST /api/v1/jobs/upload`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/status`
- `GET /api/v1/jobs/{job_id}/transcript`
- `GET /api/v1/jobs/{job_id}/summary`
- `GET /api/v1/jobs/{job_id}/pdf`
- `DELETE /api/v1/jobs/{job_id}`

---

## Data flow

1. Backend получает аудиофайл через POST /api/v1/jobs/upload
2. Создаёт job в SQLite
3. Сохраняет исходный файл в storage/source
4. Worker забирает job в обработку
5. FFmpeg нормализует аудио
6. Whisper выполняет транскрибацию
7. Backend формирует summary
8. Backend генерирует PDF отчёт
9. Статус job меняется на ready
10. Frontend получает transcript, summary и PDF через API