export interface Bucket {
  id: string;
  name: string;
  description?: string;
  enabled: boolean;
  priority: number;
  mapping_mode: string;
  immich_album_id?: string;
  classification_prompt?: string;
  examples?: string[];
  negative_examples?: string[];
  confidence_threshold?: number;
  created_at: string;
  updated_at: string;
}

export interface PromptTemplate {
  id: string;
  prompt_type: string;
  name: string;
  content: string;
  enabled: boolean;
  version: number;
  bucket_id?: string;
  created_at: string;
  updated_at: string;
}

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

export interface AssetClassification {
  id: string;
  suggested_bucket_id?: string;
  suggested_bucket_name?: string;
  confidence?: number;
  explanation?: string;
  subalbum_suggestion?: string;
  status?: string;
  provider_name?: string;
  override_bucket_id?: string;
  override_bucket_name?: string;
  created_at: string;
}

export interface AssetMetadataSuggestion {
  id: string;
  description_suggestion?: string;
  tags?: string[];
  approved_description?: string;
  approved_tags?: string[];
  writeback_status?: string;
  provider_name?: string;
}

export interface AssetDetail extends Asset {
  classification?: AssetClassification;
  metadata_suggestion?: AssetMetadataSuggestion;
}

export interface ReviewItem {
  asset_id: string;
  immich_id: string;
  original_filename?: string;
  file_created_at?: string;
  asset_type?: string;
  mime_type?: string;
  city?: string;
  country?: string;
  camera_make?: string;
  camera_model?: string;
  current_description?: string;
  current_tags?: string[];
  classification_id?: string;
  suggested_bucket_id?: string;
  suggested_bucket_name?: string;
  confidence?: number;
  explanation?: string;
  subalbum_suggestion?: string;
  review_recommended: boolean;
  classification_status: string;
  metadata_id?: string;
  description_suggestion?: string;
  tags_suggestion?: string[];
  provider_name?: string;
  prompt_run_id?: string;
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

export interface BucketStat {
  bucket_name: string;
  bucket_id?: string;
  total: number;
  by_status: Record<string, number>;
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
