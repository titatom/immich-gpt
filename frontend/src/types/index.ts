export interface Asset {
  id: string;
  immich_id: string;
  original_filename?: string;
  file_created_at?: string;
  asset_type?: string;
  mime_type?: string;
  city?: string;
  country?: string;
  camera_make?: string;
  camera_model?: string;
  description?: string;
  tags?: string[];
  album_ids?: string[];
  is_favorite: boolean;
  is_archived: boolean;
  is_external_library: boolean;
  synced_at?: string;
  created_at: string;
}

export interface JobRun {
  id: string;
  job_type: string;
  status: string;
  current_step?: string;
  progress_percent: number;
  processed_count: number;
  total_count: number;
  success_count: number;
  error_count: number;
  message?: string;
  log_lines?: string[];
  started_at?: string;
  updated_at?: string;
  completed_at?: string;
  created_at: string;
}

export interface ProviderConfig {
  id: string;
  provider_name: string;
  enabled: boolean;
  is_default: boolean;
  base_url?: string;
  model_name?: string;
  has_api_key: boolean;
  created_at: string;
  updated_at: string;
}

export interface ImmichSettings {
  immich_url: string;
  connected: boolean;
  asset_count?: number;
  error?: string;
}

export type SyncScope = "all" | "favorites" | "albums";

export interface SyncJobRequest {
  scope: SyncScope;
  album_ids?: string[];
}

export interface ImmichAlbum {
  id: string;
  albumName: string;
  assetCount: number;
}

export interface AuditLog {
  id: string;
  asset_id?: string;
  job_run_id?: string;
  action: string;
  status?: string;
  level?: string;
  source?: string;
  details_json?: Record<string, unknown>;
  error_message?: string;
  created_at: string;
}

// --- Routing tree ---
export type DestinationType =
  | "virtual"
  | "immich_album"
  | "immich_trash"
  | "review_only";

export type PrivacyAction = "allow" | "tag" | "review" | "reject";

export interface RoutingNode {
  id: string;
  parent_id?: string | null;
  name: string;
  path: string;
  is_leaf: boolean;
  description?: string | null;
  enabled: boolean;
  priority: number;
  destination_type: DestinationType;
  immich_album_name?: string | null;
  create_album_if_missing: boolean;
  auto_apply_enabled: boolean;
  auto_apply_threshold: number;
  review_below_threshold?: number | null;
  exclusive: boolean;
  allow_secondary: boolean;
  minimum_quality: "any" | "usable" | "high";
  allow_blurry: boolean;
  allow_dark: boolean;
  allow_screenshot: boolean;
  allow_duplicate: boolean;
  suggest_description: boolean;
  suggest_tags: boolean;
  suggest_location: boolean;
  suggest_caption: boolean;
  write_description: boolean;
  write_tags: boolean;
  write_location: boolean;
  custom_prompt_enabled: boolean;
  custom_prompt?: string | null;
  positive_criteria: string[];
  negative_criteria: string[];
  privacy_rules: Record<string, PrivacyAction>;
  quality_rules: Record<string, unknown>;
  automation_rules: Record<string, unknown>;
  metadata_rules: Record<string, unknown>;
  children?: RoutingNode[];
  created_at?: string;
  updated_at?: string;
}

export interface RoutingExample {
  id: string;
  bucket_id: string;
  asset_id?: string | null;
  example_type: "positive" | "negative";
  source: string;
  note?: string | null;
  created_at: string;
}

export interface RoutingPlan {
  id: string;
  job_id?: string | null;
  status: string;
  scope?: Record<string, unknown> | null;
  summary?: Record<string, unknown> | null;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface RoutingPlanItem {
  id: string;
  plan_id: string;
  asset_id: string;
  primary_bucket_id?: string | null;
  primary_bucket_path?: string | null;
  secondary_bucket_ids: string[];
  disposition: "keep" | "review" | "trash_candidate";
  confidence?: number | null;
  review_required: boolean;
  auto_apply: boolean;
  review_reasons: string[];
  reason_codes: string[];
  safety_flags: Record<string, boolean>;
  quality_flags: Record<string, boolean>;
  suggested_description?: string | null;
  suggested_tags: string[];
  suggested_location?: Record<string, unknown> | null;
  suggested_caption?: string | null;
  status: "pending" | "approved" | "rejected" | "applied" | "failed";
  error_message?: string | null;
}

export interface RoutingPlanGroupItem {
  path: string;
  bucket_id?: string | null;
  count: number;
  item_ids: string[];
}

export interface RoutingPlanSummary {
  plan_id: string;
  total: number;
  groups: {
    auto_applied: RoutingPlanGroupItem[];
    ready_to_approve: RoutingPlanGroupItem[];
    needs_review: RoutingPlanGroupItem[];
    trash_candidates: RoutingPlanGroupItem[];
    rejected: RoutingPlanGroupItem[];
    failed: RoutingPlanGroupItem[];
  };
}

export type JobStatus =
  | "queued"
  | "starting"
  | "syncing_assets"
  | "preparing_image"
  | "classifying_ai"
  | "validating_result"
  | "saving_suggestion"
  | "writing_results"
  | "completed"
  | "failed"
  | "cancelled"
  | "paused";
