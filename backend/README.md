# Transcription Portal Backend

## Stack
- FastAPI
- SQLAlchemy + SQLite (MVP)
- Background worker thread (MVP)
- FFmpeg adapter stub
- Whisper / diarization / summary service stubs ready for replacement
- PDF generation via ReportLab

## Run locally
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Key endpoints
- `POST /api/v1/jobs/upload`
- `GET /api/v1/jobs`
- `GET /api/v1/jobs/{job_id}`
- `GET /api/v1/jobs/{job_id}/status`
- `GET /api/v1/jobs/{job_id}/transcript`
- `GET /api/v1/jobs/{job_id}/summary`
- `GET /api/v1/jobs/{job_id}/pdf`
- `DELETE /api/v1/jobs/{job_id}`

## Production upgrade notes
- Replace thread worker with Celery/RQ + Redis.
- Replace stub transcription with Whisper large-v3 on GPU.
- Replace stub diarization with pyannote pipeline.
- Move SQLite to PostgreSQL.
- Move local storage to S3 / object storage.
