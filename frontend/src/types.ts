export type JobStatus =
  | 'pending'
  | 'uploading'
  | 'processing'
  | 'transcribing'
  | 'diarization'
  | 'summarizing'
  | 'pdf_ready'
  | 'ready'
  | 'cancelled'
  | 'failed';

export type StageStatus = 'waiting' | 'active' | 'completed' | 'failed';

export interface PipelineStage {
  key: string;
  label: string;
  status: StageStatus;
}

export interface SpeakerSegment {
  speaker: string;
  start: string;
  end: string;
  text: string;
}

export interface Job {
  id: string;
  title: string;
  original_filename: string;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
  status: JobStatus;
  current_stage: string;
  duration_seconds?: number | null;
  progress_percent: number;
  file_size_bytes?: number | null;
  audio_duration_seconds?: number | null;
  processing_elapsed_seconds?: number | null;
  estimated_total_seconds?: number | null;
  estimated_remaining_seconds?: number | null;
  transcript_text?: string | null;
  summary_text?: string | null;
  error_message?: string | null;
  pdf_url?: string | null;
  speaker_segments?: SpeakerSegment[];
  last_update_at?: string | null;
  heartbeat_age_seconds?: number | null;
  pipeline: PipelineStage[];
}

export interface DashboardStatsData {
  total: number;
  processing: number;
  completed: number;
  failed: number;
}

export interface JobUploadResponse {
  id: string;
  status: JobStatus;
}

export interface ModelsCatalog {
  default_model: string;
  device: string;
  download_root: string;
  installed_models: string[];
  available_to_install: string[];
  supported_models: string[];
}
