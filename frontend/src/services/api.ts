import { Job, JobUploadResponse, ModelsCatalog } from '../types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api/v1';

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with status ${response.status}`);
  }
  return (await response.json()) as T;
}

export async function fetchJobs(): Promise<Job[]> {
  const response = await fetch(`${API_BASE}/jobs`);
  const data = await parseJson<{ items: Job[] }>(response);
  return data.items;
}

export async function uploadJob(file: File, modelName?: string): Promise<JobUploadResponse> {
  const formData = new FormData();
  formData.append('file', file);
  if (modelName) {
    formData.append('model_name', modelName);
  }

  const response = await fetch(`${API_BASE}/jobs/upload`, {
    method: 'POST',
    body: formData,
  });

  return parseJson<JobUploadResponse>(response);
}

export async function fetchModelsCatalog(): Promise<ModelsCatalog> {
  const response = await fetch(`${API_BASE}/models`);
  return parseJson<ModelsCatalog>(response);
}

export async function installModel(modelName: string): Promise<void> {
  const response = await fetch(`${API_BASE}/models/install`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ model_name: modelName }),
  });
  await parseJson(response);
}

export async function cancelJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
    method: 'POST',
  });
  await parseJson(response);
}

export async function restartJob(jobId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}/restart`, {
    method: 'POST',
  });
  await parseJson(response);
}

export function buildPdfUrl(job: Job): string | null {
  if (job.pdf_url) return job.pdf_url;
  if (job.status === 'ready') return `${API_BASE}/jobs/${job.id}/pdf`;
  return null;
}
