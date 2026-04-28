import { useEffect, useMemo, useState } from 'react';
import { Job } from '../types';
import { PipelineView } from './PipelineView';
import { TranscriptPreview } from './TranscriptPreview';
import { DownloadSummaryButton } from './DownloadSummaryButton';
import { buildPdfUrl } from '../services/api';

interface JobCardProps {
  job: Job;
  onCancel: (jobId: string) => Promise<void>;
  onRestart: (jobId: string) => Promise<void>;
}

const STAGE_RU: Record<string, string> = {
  Uploading: 'Загрузка',
  Transcribing: 'Транскрибация',
  'Speaker Processing': 'Реплики',
  Summarizing: 'Сводка',
  'PDF Ready': 'PDF',
  Queued: 'В очереди',
  Processing: 'Обработка',
  Cancelled: 'Отменена',
};

function formatDateRu(value?: string | null) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleString('ru-RU');
}

/** Форматирует длительность: без лишних «3 ч» в начале — до часов только если >= 1 ч */
function formatDurationRuSec(seconds?: number | null) {
  if (seconds === null || seconds === undefined) return '—';
  if (seconds < 0) return '—';
  if (seconds < 60) return `${seconds} с`;
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  if (m < 60) {
    return s > 0 ? `${m} мин ${s} с` : `${m} мин`;
  }
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return s > 0 || rm > 0 ? `${h} ч ${rm} мин` : `${h} ч`;
}

function formatHeartbeatAgeRu(seconds?: number | null) {
  if (seconds === null || seconds === undefined) return '—';
  if (seconds < 60) return `${seconds} с назад`;
  const m = Math.floor(seconds / 60);
  const restS = seconds % 60;
  return `${m} мин ${restS} с назад`;
}

function stageToRu(stage: string) {
  return STAGE_RU[stage] ?? stage;
}

export function JobCard({ job, onCancel, onRestart }: JobCardProps) {
  const [expanded, setExpanded] = useState(job.status !== 'ready');
  const [tick, setTick] = useState(0);
  const [isActionPending, setIsActionPending] = useState(false);

  const { uiStatus, statusClass } = useMemo(() => {
    if (job.status === 'ready' || job.status === 'pdf_ready') return { uiStatus: 'Готово', statusClass: 'ready' as const };
    if (job.status === 'cancelled') return { uiStatus: 'Отмена', statusClass: 'cancelled' as const };
    if (job.status === 'failed') return { uiStatus: 'Ошибка', statusClass: 'failed' as const };
    if (job.status === 'pending') return { uiStatus: 'В очереди', statusClass: 'pending' as const };
    return { uiStatus: 'В работе', statusClass: 'processing' as const };
  }, [job.status]);

  const isActive = !['ready', 'failed', 'cancelled'].includes(job.status);

  useEffect(() => {
    setTick(0);
  }, [job.id, job.status, job.processing_elapsed_seconds]);

  useEffect(() => {
    if (!isActive) {
      return;
    }
    const id = setInterval(() => {
      setTick((v) => v + 1);
    }, 1000);
    return () => clearInterval(id);
  }, [isActive]);

  const displayElapsedSec = isActive
    ? (job.processing_elapsed_seconds ?? 0) + tick
    : (job.duration_seconds ?? null);

  const remaining = job.estimated_remaining_seconds;
  const total = job.estimated_total_seconds;
  const elapsedLine =
    isActive && (remaining != null || total != null) ? (
      <span>
        {formatDurationRuSec(displayElapsedSec)}
        {remaining != null && total != null
          ? ` (ост. ~${formatDurationRuSec(remaining)} · всего ~${formatDurationRuSec(total)})`
          : total != null
            ? ` (всего ~${formatDurationRuSec(total)})`
            : ''}
      </span>
    ) : (
      <span>{formatDurationRuSec(displayElapsedSec)}</span>
    );

  const transcriptLoading =
    !job.transcript_text && (!job.speaker_segments || job.speaker_segments.length === 0) && isActive;
  const canCancel = isActive && !isActionPending;
  const canRestart = !isActionPending;

  async function handleCancel() {
    setIsActionPending(true);
    try {
      await onCancel(job.id);
    } finally {
      setIsActionPending(false);
    }
  }

  async function handleRestart() {
    setIsActionPending(true);
    try {
      await onRestart(job.id);
    } finally {
      setIsActionPending(false);
    }
  }

  return (
    <article className="job-card">
      <div className="job-card-header">
        <div className="job-main">
          <div className="job-title-row">
            <h3>{job.title}</h3>
            <span className={`status-pill status-${statusClass}`}>{uiStatus}</span>
          </div>
          <div className="job-meta-grid">
            <span><strong>Файл:</strong> {job.original_filename}</span>
            <span><strong>Начало:</strong> {formatDateRu(job.started_at)}</span>
            <span><strong>Этап:</strong> {stageToRu(job.current_stage)}</span>
            <span><strong>Прошло:</strong> {elapsedLine}</span>
            <span><strong>Активность:</strong> {isActive ? formatHeartbeatAgeRu(job.heartbeat_age_seconds) : '—'}</span>
          </div>
        </div>

        <div className="job-actions">
          <span className="progress-label">{job.progress_percent}%</span>
          <button type="button" className="ghost-button icon-button" onClick={handleRestart} disabled={!canRestart} title="Перезапустить">
            <span className="restart-icon" aria-hidden>↻</span>
          </button>
          <button type="button" className="secondary-button" onClick={handleCancel} disabled={!canCancel}>
            Отменить
          </button>
          <button type="button" className="ghost-button" onClick={() => setExpanded((value) => !value)}>
            {expanded ? 'Свернуть' : 'Подробнее'}
          </button>
        </div>
      </div>

      {expanded && (
        <div className="job-card-details">
          <PipelineView stages={job.pipeline} />

          {job.summary_text && (
            <section className="detail-block">
              <h4>Сводка</h4>
              <p className="preserve-lines">{job.summary_text}</p>
            </section>
          )}

          <TranscriptPreview
            transcript={job.transcript_text}
            speakerSegments={job.speaker_segments}
            loading={transcriptLoading}
          />

          {job.error_message && <div className="error-banner">{job.error_message}</div>}

          <div className="detail-actions">
            <DownloadSummaryButton url={buildPdfUrl(job)} disabled={job.status !== 'ready' && job.status !== 'pdf_ready'} />
          </div>
        </div>
      )}
    </article>
  );
}
