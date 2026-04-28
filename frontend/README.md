# Transcription Web App Frontend

## Stack
- React
- TypeScript
- Vite
- REST API client (fetch / axios)
- Simple state management (hooks)

## Responsibilities

Frontend отвечает за пользовательский интерфейс и взаимодействие с backend API:

- загрузка аудиофайлов
- отображение списка задач (jobs)
- отображение статуса обработки
- просмотр транскрипта и summary
- скачивание PDF отчёта

Все данные получаются через REST API backend.

## Run locally

```bash
cd frontend
npm install
npm run dev
```

Приложение будет доступно по адресу:

`http://localhost:5173`

---

## Project structure

```text
frontend/
  src/
    components/        # UI компоненты
    services/api.ts    # работа с API
    App.tsx            # корневой компонент
```

---

## Data flow

1. Пользователь загружает файл через UI
2. Frontend отправляет POST /jobs/upload
3. Получает job_id
4. Периодически запрашивает статус (/status)
5. После завершения:
  - получает transcript
  - получает summary
  - предлагает скачать PDF