export type ResearchStatus =
  | 'PENDING_APPROVAL'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED'
  | 'CANCELLED';

export type TaskStatus =
  | 'PENDING'
  | 'RUNNING'
  | 'COMPLETED'
  | 'FAILED';

export interface ResearchPlanResponse {
  id: string;
  title: string | null;
  summary: string | null;
  content: string;
  created_at: string | null;
  updated_at: string | null;
}

export interface ResearchTaskResponse {
  id: string;
  task_key: string;
  title: string;
  angle: string | null;
  task_type: string;
  context: string | null;
  questions: string[];
  scope: string | null;
  preferred_sources: string[];
  search_budget: number;
  min_sources: number;
  depends_on: string[];
  status: TaskStatus;
  findings: string | null;
  sources: Array<{
    url?: string;
    title?: string;
    snippet?: string;
    [key: string]: unknown;
  }>;
  wave: number | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface ResearchReportResponse {
  id: string;
  content: string;
  word_count: number | null;
  created_at: string | null;
}

export interface DispatchLogResponse {
  id: string;
  task_key: string;
  wave: number;
  status: string;
  note: string | null;
  created_at: string | null;
}

export interface ResearchSessionResponse {
  id: string;
  query: string;
  status: ResearchStatus;
  created_at: string | null;
  updated_at: string | null;
  plan: ResearchPlanResponse | null;
  tasks: ResearchTaskResponse[];
  report: ResearchReportResponse | null;
  dispatch_logs: DispatchLogResponse[];
}

export interface ResearchCreateRequest {
  query: string;
}

export interface ResearchReviseRequest {
  feedback: string;
}

export interface StartResearchResponse {
  id: string;
  status: ResearchStatus;
  message: string;
}

export interface CancelResearchResponse {
  id: string;
  status: ResearchStatus;
  message: string;
}
