import axios from "axios";
import type {
  Bucket,
  PromptTemplate,
  Asset,
  ReviewItem,
  JobRun,
  ProviderConfig,
  ImmichSettings,
  AuditLog,
  BucketStat,
} from "../types";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// --- Health ---
export const getHealth = () => api.get("/health").then((r) => r.data);

// --- Settings ---
export const getImmichSettings = (): Promise<ImmichSettings> =>
  api.get("/settings/immich").then((r) => r.data);

export const saveImmichSettings = (url: string, apiKey: string): Promise<ImmichSettings> =>
  api.post("/settings/immich", { immich_url: url, immich_api_key: apiKey }).then((r) => r.data);

export const testImmichConnection = (url: string, apiKey: string) =>
  api.post("/settings/immich/test", { immich_url: url, immich_api_key: apiKey }).then((r) => r.data);

export const getProviders = (): Promise<ProviderConfig[]> =>
  api.get("/settings/providers").then((r) => r.data);

export const upsertProvider = (data: {
  provider_name: string;
  enabled?: boolean;
  is_default?: boolean;
  api_key?: string;
  base_url?: string;
  model_name?: string;
}) => api.post("/settings/providers", data).then((r) => r.data);

export const deleteProvider = (name: string) =>
  api.delete(`/settings/providers/${name}`).then((r) => r.data);

export const testProvider = (name: string) =>
  api.get(`/settings/providers/${name}/test`).then((r) => r.data);

export const getProviderModels = (name: string): Promise<Array<{ id: string; name: string }>> =>
  api.get(`/settings/providers/${name}/models`).then((r) => r.data);

// --- Buckets ---
export const getBuckets = (): Promise<Bucket[]> =>
  api.get("/buckets").then((r) => r.data);

export const createBucket = (data: Partial<Bucket>): Promise<Bucket> =>
  api.post("/buckets", data).then((r) => r.data);

export const updateBucket = (id: string, data: Partial<Bucket>): Promise<Bucket> =>
  api.patch(`/buckets/${id}`, data).then((r) => r.data);

export const deleteBucket = (id: string) =>
  api.delete(`/buckets/${id}`).then((r) => r.data);

// --- Prompts ---
export const getPrompts = (params?: { prompt_type?: string; bucket_id?: string }): Promise<PromptTemplate[]> =>
  api.get("/prompts", { params }).then((r) => r.data);

export const createPrompt = (data: Partial<PromptTemplate>): Promise<PromptTemplate> =>
  api.post("/prompts", data).then((r) => r.data);

export const updatePrompt = (id: string, data: Partial<PromptTemplate>): Promise<PromptTemplate> =>
  api.patch(`/prompts/${id}`, data).then((r) => r.data);

export const deletePrompt = (id: string) =>
  api.delete(`/prompts/${id}`).then((r) => r.data);

// --- Assets ---
export const getAssets = (params?: { page?: number; page_size?: number; asset_type?: string }) =>
  api.get("/assets", { params }).then((r) => r.data as Asset[]);

export const getAssetCount = () =>
  api.get("/assets/count").then((r) => r.data as { count: number });

// --- Jobs ---
export const getJobs = (params?: { job_type?: string; status?: string; limit?: number }): Promise<JobRun[]> =>
  api.get("/jobs", { params }).then((r) => r.data);

export const getJob = (id: string): Promise<JobRun> =>
  api.get(`/jobs/${id}`).then((r) => r.data);

export const startSyncJob = () =>
  api.post("/jobs/sync").then((r) => r.data as { job_id: string; status: string });

export const startClassifyJob = (params?: { asset_ids?: string[]; limit?: number; force?: boolean }) =>
  api.post("/jobs/classify", null, { params }).then((r) => r.data as { job_id: string; status: string });

export const cancelJob = (id: string) =>
  api.post(`/jobs/${id}/cancel`).then((r) => r.data);

// --- Review ---
export const getReviewQueue = (params?: {
  status?: string;
  bucket_id?: string;
  page?: number;
  page_size?: number;
}): Promise<ReviewItem[]> =>
  api.get("/review/queue", { params }).then((r) => r.data);

export const getReviewCount = (status = "pending_review") =>
  api.get("/review/queue/count", { params: { status } }).then((r) => r.data as { count: number });

export const getReviewItem = (assetId: string): Promise<ReviewItem> =>
  api.get(`/review/item/${assetId}`).then((r) => r.data);

export const approveAsset = (
  assetId: string,
  data: {
    approved_bucket_id?: string;
    approved_bucket_name?: string;
    approved_description?: string;
    approved_tags?: string[];
    approved_subalbum?: string;
    subalbum_approved?: boolean;
    trigger_writeback?: boolean;
  }
) => api.post(`/review/item/${assetId}/approve`, data).then((r) => r.data);

export const rejectAsset = (assetId: string) =>
  api.post(`/review/item/${assetId}/reject`).then((r) => r.data);

export const bulkReview = (data: {
  asset_ids: string[];
  action: "approve_all" | "reject_all";
  trigger_writeback?: boolean;
}) => api.post("/review/bulk", data).then((r) => r.data);

// --- Albums ---
export const getAlbums = () =>
  api.get("/albums").then((r) => r.data as Array<{ id: string; albumName: string; assetCount: number }>);

// --- Audit Logs ---
export const getAuditLogs = (params?: {
  asset_id?: string;
  job_run_id?: string;
  action?: string;
  status?: string;
  page?: number;
  page_size?: number;
}): Promise<AuditLog[]> =>
  api.get("/audit-logs", { params }).then((r) => r.data);

export const getAuditLogCount = (params?: {
  asset_id?: string;
  job_run_id?: string;
  status?: string;
}) =>
  api.get("/audit-logs/count", { params }).then((r) => r.data as { count: number });

// --- Bucket stats ---
export const getBucketStats = (): Promise<BucketStat[]> =>
  api.get("/buckets/stats").then((r) => r.data);

// --- Thumbnail URL helper ---
export const getThumbnailUrl = (assetId: string, size = "thumbnail") =>
  `/api/thumbnails/${assetId}?size=${size}`;
