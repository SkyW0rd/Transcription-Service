import { ChangeEvent, DragEvent, useEffect, useMemo, useState } from 'react';
import { ModelsCatalog } from '../types';

interface NewJobPanelProps {
  open: boolean;
  isSubmitting: boolean;
  error?: string | null;
  modelsCatalog: ModelsCatalog | null;
  modelsLoading: boolean;
  modelsError?: string | null;
  onInstallModel: (modelName: string) => Promise<void>;
  onSubmit: (file: File, modelName: string) => Promise<void>;
  onClose: () => void;
}

const ACCEPTED_TYPES = '.mp3,.wav,.m4a,.ogg,.mp4,.aac,.flac,.webm';
const MODEL_SIZES_MB: Record<string, number> = {
  tiny: 75,
  base: 145,
  small: 465,
  medium: 1500,
  large: 3000,
};
const ESTIMATED_MBPS = 8;

function formatEstimate(modelName: string): string {
  const sizeMb = MODEL_SIZES_MB[modelName] ?? 500;
  const minutes = Math.ceil(sizeMb / ESTIMATED_MBPS / 60);
  return `~${minutes} мин`;
}

function formatSecondsRu(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m > 0) return `${m} мин ${s} с`;
  return `${s} с`;
}

export function NewJobPanel({
  open,
  isSubmitting,
  error,
  modelsCatalog,
  modelsLoading,
  modelsError,
  onInstallModel,
  onSubmit,
  onClose,
}: NewJobPanelProps) {
  const [file, setFile] = useState<File | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);
  const [selectedModel, setSelectedModel] = useState<string>('');
  const [installingModel, setInstallingModel] = useState<string | null>(null);
  const [installElapsedSec, setInstallElapsedSec] = useState(0);

  const jobTitle = useMemo(() => {
    if (!file) return '—';
    const name = file.name.replace(/\.[^.]+$/, '');
    return name || file.name;
  }, [file]);

  useEffect(() => {
    if (!modelsCatalog) return;
    if (selectedModel && modelsCatalog.supported_models.includes(selectedModel)) return;
    setSelectedModel(modelsCatalog.default_model || modelsCatalog.supported_models[0] || '');
  }, [modelsCatalog, selectedModel]);

  useEffect(() => {
    if (!installingModel) return;
    const timer = setInterval(() => {
      setInstallElapsedSec((value) => value + 1);
    }, 1000);
    return () => clearInterval(timer);
  }, [installingModel]);

  function validate(nextFile: File | null) {
    if (!nextFile) {
      setLocalError('Выберите аудиофайл.');
      return false;
    }

    const extension = nextFile.name.split('.').pop()?.toLowerCase();
    const allowed = ['mp3', 'wav', 'm4a', 'ogg', 'mp4', 'aac', 'flac', 'webm'];
    if (!extension || !allowed.includes(extension)) {
      setLocalError('Неподдерживаемый формат. Допустимы: MP3, WAV, M4A, OGG, MP4, AAC, FLAC, WEBM.');
      return false;
    }

    if (nextFile.size > 1024 * 1024 * 1024) {
      setLocalError('Файл слишком большой (максимум 1 ГБ).');
      return false;
    }

    setLocalError(null);
    return true;
  }

  function handleFileChange(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0] ?? null;
    setFile(nextFile);
    validate(nextFile);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    const nextFile = event.dataTransfer.files?.[0] ?? null;
    setFile(nextFile);
    validate(nextFile);
  }

  async function handleSubmit() {
    if (!validate(file)) return;
    if (!selectedModel) {
      setLocalError('Выберите модель Whisper.');
      return;
    }
    if (!modelsCatalog?.installed_models.includes(selectedModel)) {
      setLocalError(`Модель «${selectedModel}» не установлена. Сначала установите её.`);
      return;
    }
    await onSubmit(file!, selectedModel);
    setFile(null);
  }

  async function handleInstallModel() {
    if (!selectedModel) return;
    setLocalError(null);
    setInstallElapsedSec(0);
    setInstallingModel(selectedModel);
    try {
      await onInstallModel(selectedModel);
    } catch (installError) {
      setLocalError(installError instanceof Error ? installError.message : 'Не удалось установить модель.');
    } finally {
      setInstallingModel(null);
    }
  }

  if (!open) return null;

  return (
    <section className="panel-card panel-card-accent" aria-label="Новая задача">
      <div className="panel-header-row">
        <div>
          <h2>Новая задача</h2>
          <p>Загрузите один аудио- или видеофайл. Название задачи берётся из имени файла.</p>
        </div>
        <button type="button" className="ghost-button" onClick={onClose}>
          Закрыть
        </button>
      </div>

      <label
        className="dropzone"
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        <input type="file" accept={ACCEPTED_TYPES} onChange={handleFileChange} hidden />
        <span className="dropzone-title">Перетащите файл сюда</span>
        <span className="dropzone-subtitle">или нажмите, чтобы выбрать</span>
        <span className="dropzone-formats">Форматы: MP3, WAV, M4A, OGG, MP4, AAC, FLAC, WEBM</span>
      </label>

      <div className="new-job-meta">
        <div>
          <span className="meta-label">Название задачи</span>
          <strong>{jobTitle}</strong>
        </div>
        <div>
          <span className="meta-label">Выбранный файл</span>
          <strong>{file?.name ?? 'не выбран'}</strong>
        </div>
      </div>

      <div className="new-job-meta">
        <div>
          <span className="meta-label">Модель Whisper</span>
          <select
            value={selectedModel}
            onChange={(event) => setSelectedModel(event.target.value)}
            disabled={isSubmitting || modelsLoading || !!installingModel}
          >
            {(modelsCatalog?.supported_models || []).map((model) => (
              <option key={model} value={model}>
                {model}
              </option>
            ))}
          </select>
        </div>
        <div>
          <span className="meta-label">Статус модели</span>
          <strong>
            {selectedModel && modelsCatalog?.installed_models.includes(selectedModel) ? 'установлена' : 'не установлена'}
          </strong>
        </div>
      </div>

      <div className="new-job-meta">
        <div>
          <span className="meta-label">Установлено моделей</span>
          <strong>{modelsCatalog ? `${modelsCatalog.installed_models.length} / ${modelsCatalog.supported_models.length}` : '—'}</strong>
        </div>
        <div>
          <span className="meta-label">Примерное время скачивания</span>
          <strong>{selectedModel ? formatEstimate(selectedModel) : '—'}</strong>
        </div>
      </div>

      {installingModel && (
        <div className="panel-card">
          Установка «<strong>{installingModel}</strong>»… прошло {formatSecondsRu(installElapsedSec)} (оценка {formatEstimate(installingModel)})
        </div>
      )}

      {(localError || error || modelsError) && <div className="error-banner">{localError || error || modelsError}</div>}

      <div className="panel-actions">
        <button
          type="button"
          className="secondary-button"
          onClick={handleInstallModel}
          disabled={!selectedModel || isSubmitting || modelsLoading || !!installingModel || !!modelsCatalog?.installed_models.includes(selectedModel)}
        >
          {installingModel ? 'Установка…' : 'Установить модель'}
        </button>
        <button type="button" className="secondary-button" onClick={onClose}>
          Отмена
        </button>
        <button type="button" className="primary-button" disabled={isSubmitting} onClick={handleSubmit}>
          {isSubmitting ? 'Запуск…' : 'Запустить'}
        </button>
      </div>
    </section>
  );
}
