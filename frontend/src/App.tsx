import { useEffect, useMemo, useState } from 'react';
import { DashboardStats } from './components/DashboardStats';
import { NewJobPanel } from './components/NewJobPanel';
import { JobList } from './components/JobList';
import { DashboardStatsData, Job, ModelsCatalog } from './types';
import { cancelJob, fetchJobs, fetchModelsCatalog, installModel, restartJob, uploadJob } from './services/api';

function computeStats(jobs: Job[]): DashboardStatsData {
  return {
    total: jobs.length,
    processing: jobs.filter((job) => !['ready', 'failed', 'pdf_ready', 'cancelled'].includes(job.status)).length,
    completed: jobs.filter((job) => ['ready', 'pdf_ready'].includes(job.status)).length,
    failed: jobs.filter((job) => job.status === 'failed' || job.status === 'cancelled').length,
  };
}

export default function App() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [modelsCatalog, setModelsCatalog] = useState<ModelsCatalog | null>(null);
  const [modelsLoading, setModelsLoading] = useState(true);
  const [modelsError, setModelsError] = useState<string | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function loadJobs(options: { showLoader?: boolean } = {}) {
    if (options.showLoader ?? true) {
      setLoading(true);
    }
    setError(null);
    try {
      const items = await fetchJobs();
      setJobs(items);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Не удалось загрузить задачи.');
    } finally {
      if (options.showLoader ?? true) {
        setLoading(false);
      }
    }
  }

  useEffect(() => {
    void loadJobs({ showLoader: true });
  }, []);

  async function loadModels() {
    setModelsLoading(true);
    setModelsError(null);
    try {
      const catalog = await fetchModelsCatalog();
      setModelsCatalog(catalog);
    } catch (requestError) {
      setModelsError(requestError instanceof Error ? requestError.message : 'Не удалось загрузить модели.');
    } finally {
      setModelsLoading(false);
    }
  }

  useEffect(() => {
    void loadModels();
  }, []);

  useEffect(() => {
    const hasActiveJobs = jobs.some((job) => !['ready', 'failed', 'cancelled'].includes(job.status));
    if (!hasActiveJobs) return;

    const timer = setInterval(() => {
      void loadJobs({ showLoader: false });
    }, 3000);

    return () => clearInterval(timer);
  }, [jobs]);

  async function handleInstallModel(modelName: string) {
    setModelsError(null);
    try {
      await installModel(modelName);
      await loadModels();
    } catch (requestError) {
      setModelsError(requestError instanceof Error ? requestError.message : 'Не удалось установить модель.');
      throw requestError;
    }
  }

  async function handleCreateJob(file: File, modelName: string) {
    setIsSubmitting(true);
    setUploadError(null);
    try {
      await uploadJob(file, modelName);
      setPanelOpen(false);
      await loadJobs({ showLoader: true });
    } catch (requestError) {
      setUploadError(requestError instanceof Error ? requestError.message : 'Не удалось создать задачу.');
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleCancelJob(jobId: string) {
    setError(null);
    try {
      await cancelJob(jobId);
      await loadJobs({ showLoader: false });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Не удалось отменить задачу.');
      throw requestError;
    }
  }

  async function handleRestartJob(jobId: string) {
    setError(null);
    try {
      await restartJob(jobId);
      await loadJobs({ showLoader: false });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Не удалось перезапустить задачу.');
      throw requestError;
    }
  }

  const stats = useMemo(() => computeStats(jobs), [jobs]);

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">Распознавание речи и отчёты</span>
          <h1>Transcription Portal</h1>
        </div>

        <div className="topbar-actions">
          <span className="service-badge online">Сервис доступен</span>
          <button type="button" className="ghost-button" onClick={() => void loadJobs()}>
            Обновить
          </button>
          <button type="button" className="primary-button" onClick={() => setPanelOpen((value) => !value)}>
            {panelOpen ? 'Скрыть панель' : 'Новая задача'}
          </button>
        </div>
      </header>

      <DashboardStats stats={stats} />

      <NewJobPanel
        open={panelOpen}
        isSubmitting={isSubmitting}
        error={uploadError}
        modelsCatalog={modelsCatalog}
        modelsLoading={modelsLoading}
        modelsError={modelsError}
        onInstallModel={handleInstallModel}
        onSubmit={handleCreateJob}
        onClose={() => setPanelOpen(false)}
      />

      <section className="section-header">
        <div>
          <h2>Задачи</h2>
          <p>
            Загрузка аудио, этапы обработки, предпросмотр текста и скачивание PDF.
          </p>
        </div>
      </section>

      <JobList
        jobs={jobs}
        loading={loading}
        error={error}
        onCancel={handleCancelJob}
        onRestart={handleRestartJob}
      />
    </div>
  );
}
