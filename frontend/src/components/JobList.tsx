import { Job } from '../types';
import { JobCard } from './JobCard';

interface JobListProps {
  jobs: Job[];
  loading: boolean;
  error?: string | null;
  onCancel: (jobId: string) => Promise<void>;
  onRestart: (jobId: string) => Promise<void>;
}

export function JobList({ jobs, loading, error, onCancel, onRestart }: JobListProps) {
  if (loading) {
    return <div className="panel-card">Загрузка списка…</div>;
  }

  if (error) {
    return <div className="error-banner">{error}</div>;
  }

  if (jobs.length === 0) {
    return (
      <div className="empty-state">
        <h3>Задач пока нет</h3>
        <p>Загрузите аудиофайл, чтобы начать распознавание.</p>
      </div>
    );
  }

  return (
    <section className="job-list">
      {jobs.map((job) => (
        <JobCard key={job.id} job={job} onCancel={onCancel} onRestart={onRestart} />
      ))}
    </section>
  );
}
