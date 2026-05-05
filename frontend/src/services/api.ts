import axios from "axios";
import type {
  Asset,
  JobRun,
  ProviderConfig,
  ImmichSettings,
  SyncJobRequest,
  ImmichAlbum,
  AuditLog,
  RoutingNode,
  RoutingExample,
  RoutingPlan,
  RoutingPlanItem,
  RoutingPlanSummary,
} from "../types";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
  withCredentials: true,
});

// Public paths where a 401 is expected and must not trigger a redirect.
const PUBLIC_PATHS = ["/login", "/setup", "/forgot-password", "/reset-password"];

// Redirect to login on 401, but only when the user is on a protected page.
// Cancelled requests (AbortController) are silently ignored.
api.interceptors.response.use(
  res => res,
  err => {
    if (axios.isCancel(err)) return Promise.reject(err);
    const isPublicPath = PUBLIC_PATHS.some(p => window.location.pathname.startsWith(p));
    if (err?.response?.status === 401 && !isPublicPath) {
      window.location.href = "/login";
    }
    return Promise.reject(err);
  }
);

// --- Auth ---
export interface AuthUser {
  id: string;
  email: string;
  username: string;
  role: "admin" | "user";
  force_password_change: boolean;
}

export const login = (username: string, password: string): Promise<AuthUser> =>
  api.post("/auth/login", { username, password }).then(r => r.data);

export const logout = () =>
  api.post("/auth/logout").then(r => r.data);

export const getCurrentUser = (signal?: AbortSignal): Promise<AuthUser> =>
  api.get("/auth/me", { signal }).then(r => r.data);

export const changePassword = (current_password: string, new_password: string) =>
  api.post("/auth/change-password", { current_password, new_password }).then(r => r.data);

export const forgotPassword = (email: string) =>
  api.post("/auth/forgot-password", { email }).then(r => r.data);

export const resetPassword = (token: string, new_password: string) =>
  api.post("/auth/reset-password", { token, new_password }).then(r => r.data);

export const getSetupStatus = (): Promise<{ setup_required: boolean }> =>
  api.get("/auth/setup/status").then(r => r.data);

export const setupCreateAdmin = (data: { email: string; username: string; password: string }): Promise<AuthUser> =>
  api.post("/auth/setup", data).then(r => r.data);

// --- Admin ---
export const adminListUsers = () =>
  api.get("/admin/users").then(r => r.data);

export const adminCreateUser = (data: {
  email: string;
  username: string;
  password: string;
  role: string;
  force_password_change: boolean;
}) => api.post("/admin/users", data).then(r => r.data);

export const adminUpdateUser = (userId: string, data: { is_active?: boolean; force_password_change?: boolean }) =>
  api.patch(`/admin/users/${userId}`, data).then(r => r.data);

export const adminResetPassword = (userId: string, new_password?: string) =>
  api.post(`/admin/users/${userId}/reset-password`, { new_password: new_password ?? null }).then(r => r.data);

export const adminDeleteUser = (userId: string) =>
  api.delete(`/admin/users/${userId}`).then(r => r.data);

// --- Health ---
export const getHealth = () => api.get("/health").then((r) => r.data);

// --- Settings ---
export const getImmichSettings = (): Promise<ImmichSettings> =>
  api.get("/settings/immich").then((r) => r.data);

export const saveImmichSettings = (url: string, apiKey: string): Promise<ImmichSettings> =>
  api.post("/settings/immich", { immich_url: url, immich_api_key: apiKey }).then((r) => r.data);

export interface RoutingPreferences {
  learn_from_corrections: boolean;
}
export const getRoutingPreferences = (): Promise<RoutingPreferences> =>
  api.get("/settings/routing").then((r) => r.data);

export const saveRoutingPreferences = (data: RoutingPreferences): Promise<RoutingPreferences> =>
  api.post("/settings/routing", data).then((r) => r.data);

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

// --- Assets ---
export const getAssets = (params?: {
  page?: number;
  page_size?: number;
  asset_type?: string;
  q?: string;
}) => api.get("/assets", { params }).then((r) => r.data as Asset[]);

export const getAssetCount = (params?: {
  asset_type?: string;
  q?: string;
}) => api.get("/assets/count", { params }).then((r) => r.data as { count: number });

export const getAllAssetIds = (params?: {
  asset_type?: string;
  q?: string;
}) => api.get("/assets/ids", { params }).then((r) => r.data as { ids: string[] });

// --- Jobs ---
export const getJobs = (params?: { job_type?: string; status?: string; limit?: number }): Promise<JobRun[]> =>
  api.get("/jobs", { params }).then((r) => r.data);

export const getJob = (id: string): Promise<JobRun> =>
  api.get(`/jobs/${id}`).then((r) => r.data);

export const startSyncJob = (params?: SyncJobRequest) =>
  api.post("/jobs/sync", params ?? {}).then((r) => r.data as { job_id: string; status: string });

export const cancelJob = (id: string) =>
  api.post(`/jobs/${id}/cancel`).then((r) => r.data);

export const pauseJob = (id: string) =>
  api.post(`/jobs/${id}/pause`).then((r) => r.data);

export const resumeJob = (id: string) =>
  api.post(`/jobs/${id}/resume`).then((r) => r.data);

export const deleteJob = (id: string) =>
  api.delete(`/jobs/${id}`).then((r) => r.data);

export const clearTerminalJobs = () =>
  api.delete("/jobs").then((r) => r.data as { deleted: number });

// --- Albums ---
export const getAlbums = () =>
  api.get("/albums").then((r) => r.data as ImmichAlbum[]);

// --- Audit Logs ---
export const getAuditLogs = (params?: {
  asset_id?: string;
  job_run_id?: string;
  action?: string;
  status?: string;
  level?: string;
  source?: string;
  q?: string;
  page?: number;
  page_size?: number;
}): Promise<AuditLog[]> =>
  api.get("/audit-logs", { params }).then((r) => r.data);

export const getAuditLogCount = (params?: {
  asset_id?: string;
  job_run_id?: string;
  status?: string;
  level?: string;
}) =>
  api.get("/audit-logs/count", { params }).then((r) => r.data as { count: number });

// --- Routing tree ---
export const getRoutingTree = (): Promise<{ nodes: RoutingNode[] }> =>
  api.get("/routing/tree").then((r) => r.data);

export const listRoutingNodes = (): Promise<RoutingNode[]> =>
  api.get("/routing/nodes").then((r) => r.data);

export const createRoutingNode = (data: Partial<RoutingNode>): Promise<RoutingNode> =>
  api.post("/routing/nodes", data).then((r) => r.data);

export const updateRoutingNode = (id: string, data: Partial<RoutingNode>): Promise<RoutingNode> =>
  api.patch(`/routing/nodes/${id}`, data).then((r) => r.data);

export const deleteRoutingNode = (id: string, cascade = false) =>
  api.delete(`/routing/nodes/${id}`, { params: { cascade } }).then((r) => r.data);

export const moveRoutingNode = (id: string, new_parent_id: string | null): Promise<RoutingNode> =>
  api.post(`/routing/nodes/${id}/move`, { new_parent_id }).then((r) => r.data);

export const duplicateRoutingNode = (id: string): Promise<RoutingNode> =>
  api.post(`/routing/nodes/${id}/duplicate`).then((r) => r.data);

export const listRoutingExamples = (nodeId: string): Promise<RoutingExample[]> =>
  api.get(`/routing/nodes/${nodeId}/examples`).then((r) => r.data);

export const addRoutingExample = (
  nodeId: string,
  data: { asset_id?: string; example_type: "positive" | "negative"; note?: string; source?: string }
): Promise<RoutingExample> =>
  api.post(`/routing/nodes/${nodeId}/examples`, data).then((r) => r.data);

export const deleteRoutingExample = (exampleId: string) =>
  api.delete(`/routing/examples/${exampleId}`).then((r) => r.data);

export const getRoutingPromptPreview = (nodeId: string): Promise<{ bucket_id: string; path: string; compiled_prompt: string }> =>
  api.get(`/routing/nodes/${nodeId}/prompt-preview`).then((r) => r.data);

export const startRoutingClassify = (data?: {
  asset_ids?: string[];
  limit?: number;
  force?: boolean;
}) =>
  api.post("/routing/classify", data ?? {}).then(
    (r) => r.data as { job_id: string; plan_id: string; status: string }
  );

export const listRoutingPlans = (params?: { status?: string }): Promise<RoutingPlan[]> =>
  api.get("/routing/plans", { params }).then((r) => r.data);

export const getRoutingPlan = (planId: string): Promise<RoutingPlan> =>
  api.get(`/routing/plans/${planId}`).then((r) => r.data);

export const getRoutingPlanSummary = (planId: string): Promise<RoutingPlanSummary> =>
  api.get(`/routing/plans/${planId}/summary`).then((r) => r.data);

export const getRoutingPlanItems = (
  planId: string,
  params?: { status?: string; bucket_id?: string }
): Promise<RoutingPlanItem[]> =>
  api.get(`/routing/plans/${planId}/items`, { params }).then((r) => r.data);

export const approveRoutingPlanItems = (
  planId: string,
  data: { item_ids?: string[]; bucket_id?: string }
) => api.post(`/routing/plans/${planId}/approve`, data).then((r) => r.data);

export const rejectRoutingPlanItems = (
  planId: string,
  data: { item_ids?: string[]; bucket_id?: string }
) => api.post(`/routing/plans/${planId}/reject`, data).then((r) => r.data);

export const moveRoutingPlanItems = (
  planId: string,
  data: { item_ids: string[]; target_bucket_id: string }
) => api.post(`/routing/plans/${planId}/items/move`, data).then((r) => r.data);

export const applyRoutingPlan = (planId: string) =>
  api.post(`/routing/plans/${planId}/apply`).then((r) => r.data);

// --- Thumbnail URL helper ---
export const getThumbnailUrl = (assetId: string, size = "thumbnail") =>
  `/api/thumbnails/${assetId}?size=${size}`;
