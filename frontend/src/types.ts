export interface Recipe {
  id: string; label: string; icon: string; promise: string;
  needs: string[]; needs_labels: Record<string, string>;
  steps: { id: string; label: string; engine: string }[];
}
export interface Take {
  id: string; kind: string; mime: string; bytes: number; rating: number;
  meta: { engine?: string; simulated?: boolean }; created_at: string;
}
export interface Shot {
  id: string; project_id: string; idx: number; kind: string; title: string;
  duration_s: number; dialogue: string; prompt: string;
  character_id: string | null; voice_id: string | null; source_asset_id: string | null;
  status: string; selected_artifact: string | null;
  qc: { verdict?: string; checks?: { id: string; status: string; detail: string }[]; human_checks?: string[] };
  human_review: { checks?: Record<string, boolean>; score?: number; notes?: string; verdict?: string };
  takes: Take[];
}
export interface Asset {
  id: string; name: string; kind: string; role: string; project_id: string | null;
  rights_note: string; meta: { analysis?: { media?: Record<string, unknown>; warnings?: string[]; thumbnails?: string[] } };
  created_at: string;
}
export interface ExportItem {
  id: string; path: string; created_at: string;
  spec: { contains_simulation?: boolean; clips?: number };
  qc: { verdict?: string };
}
export interface Project {
  id: string; name: string; brief: string; recipe: string; format: string;
  quality: string; status: string;
  settings: { inputs?: Record<string, string> };
  shots: Shot[]; assets: Asset[]; exports: ExportItem[];
  shots_count?: number; exports_count?: number; created_at: string;
}
export interface Job {
  id: string; type: string; engine: string; status: string; progress: number;
  stage: string; error: string | null; simulated: number; shot_id: string | null;
  project_id: string | null; cost_usd: number; created_at: string; log?: string[];
}
export interface Character { id: string; name: string; description: string; ref_asset_id: string | null; consent: number; }
export interface Voice { id: string; name: string; language: string; ref_asset_id: string | null; transcript: string; consent: number; }
export interface EngineInfo {
  name: string; kind: string; label: string; available: boolean; unavailable_reason: string;
  simulated: boolean; verified: boolean; maturity: string; gpu: string; provider: string; notes: string;
}
export interface PlanStep { id: string; label: string; engine: string; skipped: boolean; skip_reason: string; available: boolean; blocker: string; quality_note?: string; }
export interface Plan {
  recipe: string; label: string; quality: string; steps: PlanStep[];
  missing_inputs: { id: string; label: string }[]; blockers: string[]; ready: boolean;
  requires_gpu_spend: boolean;
  estimate: { video_seconds: number; gpu_seconds: number; cost_usd: number; basis: string };
}
