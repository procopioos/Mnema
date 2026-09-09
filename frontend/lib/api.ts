import type { components } from "./api/generated";

export type AdminMemberOut = components["schemas"]["AdminMemberOut"];
export type AdminStatsOut = components["schemas"]["AdminStatsOut"];
export type AdminUserOut = components["schemas"]["AdminUserOut"];
export type AdminWorkspaceOut = components["schemas"]["AdminWorkspaceOut"];
export type AuditAction = components["schemas"]["AuditAction"];
export type AuditLogListResponse = components["schemas"]["AuditLogListResponse"];
export type AuditLogOut = components["schemas"]["AuditLogOut"];
export type AuthResponse = components["schemas"]["AuthResponse"];
export type DocumentOut = components["schemas"]["DocumentOut"];
export type DocumentListResponse = components["schemas"]["DocumentListResponse"];
export type DocumentPageOut = components["schemas"]["DocumentPageOut"];
export type DocumentStatus = components["schemas"]["DocumentStatus"];
export type PublicDocumentListResponse = components["schemas"]["PublicDocumentListResponse"];
export type PublicDocumentOut = components["schemas"]["PublicDocumentOut"];
export type FolderOut = components["schemas"]["FolderOut"];
export type Role = components["schemas"]["Role"];
export type TagOut = components["schemas"]["TagOut"];
export type TagScope = "global" | "user";
export type UserOut = components["schemas"]["UserOut"];
export type WorkspaceMember = components["schemas"]["WorkspaceMemberPublic"];
export type WorkspaceOut = components["schemas"]["WorkspaceOut"];

const BASE = "/api/v1";
const TOKEN_KEY = "mnema.access_token";
const REFRESH_KEY = "mnema.refresh_token";
const OLD_TOKEN_KEY = "verity.access_token";
const OLD_REFRESH_KEY = "verity.refresh_token";

let migrated = false;
function migrateLegacyTokens() {
  if (migrated) return;
  migrated = true;
  try {
    if (!localStorage.getItem(TOKEN_KEY) && localStorage.getItem(OLD_TOKEN_KEY)) {
      localStorage.setItem(TOKEN_KEY, localStorage.getItem(OLD_TOKEN_KEY)!);
    }
    if (!localStorage.getItem(REFRESH_KEY) && localStorage.getItem(OLD_REFRESH_KEY)) {
      localStorage.setItem(REFRESH_KEY, localStorage.getItem(OLD_REFRESH_KEY)!);
    }
    localStorage.removeItem(OLD_TOKEN_KEY);
    localStorage.removeItem(OLD_REFRESH_KEY);
  } catch { /* storage unavailable */ }
}

export const tokenStore = {
  getAccess: () => { migrateLegacyTokens(); return localStorage.getItem(TOKEN_KEY); },
  getRefresh: () => { migrateLegacyTokens(); return localStorage.getItem(REFRESH_KEY); },
  set: (access: string, refresh: string) => {
    localStorage.setItem(TOKEN_KEY, access);
    localStorage.setItem(REFRESH_KEY, refresh);
  },
  clear: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_KEY);
  },
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function parseError(response: Response): Promise<ApiError> {
  let message = `Request failed (${response.status})`;
  try {
    const body = await response.json();
    if (typeof body.detail === "string") message = body.detail;
    else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join("; ");
  } catch {
    // non-JSON error body; keep the default message
  }
  return new ApiError(response.status, message);
}

const inflightGets = new Map<string, Promise<unknown>>();

function normalizeCacheKey(path: string): string {
  const [base, query] = path.split("?");
  if (!query) return base;
  const params = new URLSearchParams(query);
  params.sort();
  return `${base}?${params.toString()}`;
}

async function request<T>(path: string, init: RequestInit = {}, retry = true, raw = false): Promise<T> {
  const isGet = init.method === undefined || init.method === "GET";
  const cacheKey = isGet ? normalizeCacheKey(path) : "";
  if (retry && isGet && inflightGets.has(cacheKey)) return inflightGets.get(cacheKey) as Promise<T>;

  const headers = new Headers(init.headers);
  const access = tokenStore.getAccess();
  if (access) headers.set("Authorization", `Bearer ${access}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");

  const promise = (async () => {
    try {
      const response = await fetch(`${BASE}${path}`, { ...init, headers });

      if (response.status === 401 && retry && tokenStore.getRefresh()) {
        const refreshed = await refreshAccess();
        if (refreshed) return request<T>(path, init, false, raw);
      }
      if (!response.ok) throw await parseError(response);
      if (response.status === 204) return undefined as T;
      if (raw) return (await response.blob()) as T;
      return (await response.json()) as T;
    } finally {
      if (isGet) inflightGets.delete(cacheKey);
    }
  })();

  if (isGet) inflightGets.set(cacheKey, promise);
  return promise;
}

let refreshLock: Promise<boolean> | null = null;

function refreshAccess(): Promise<boolean> {
  if (refreshLock) return refreshLock;
  refreshLock = (async () => {
    const refresh = tokenStore.getRefresh();
    if (!refresh) return false;
    try {
      const response = await fetch(`${BASE}/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refresh }),
      });
      if (!response.ok) {
        tokenStore.clear();
        return false;
      }
      const data = (await response.json()) as { access_token: string; refresh_token: string };
      tokenStore.set(data.access_token, data.refresh_token);
      return true;
    } catch {
      tokenStore.clear();
      return false;
    } finally {
      refreshLock = null;
    }
  })();
  return refreshLock;
}

export const auth = {
  register: (payload: { email: string; password: string; full_name: string }) =>
    request<AuthResponse>("/auth/register", { method: "POST", body: JSON.stringify(payload) }),

  login: (payload: { email: string; password: string }) =>
    request<AuthResponse>("/auth/login", { method: "POST", body: JSON.stringify(payload) }),

  me: () => request<UserOut>("/auth/me"),
};

export const setup = {
  status: () => request<{ required: boolean }>("/setup"),
};

export const admin = {
  reset: () => request<void>("/admin/reset", { method: "POST" }),
  stats: () => request<AdminStatsOut>("/admin/stats"),
  users: (q?: string) => {
    const qs = q ? `?q=${encodeURIComponent(q)}` : "";
    return request<AdminUserOut[]>(`/admin/users${qs}`);
  },
  updateUser: (id: string, payload: { is_system_admin?: boolean }) =>
    request<AdminUserOut>(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),

  audit: (params: { workspaceId?: string; limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.workspaceId) query.set("workspace_id", params.workspaceId);
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<AuditLogListResponse>(`/admin/audit${qs ? `?${qs}` : ""}`);
  },

  workspaces: {
    list: () => request<AdminWorkspaceOut[]>("/admin/workspaces"),
    create: (payload: { name: string; owner_id?: string | null }) =>
      request<AdminWorkspaceOut>("/admin/workspaces", {
        method: "POST",
        body: JSON.stringify(payload),
      }),
    update: (id: string, payload: { name?: string; max_documents?: number; max_storage_bytes?: number }) =>
      request<AdminWorkspaceOut>(`/admin/workspaces/${id}`, {
        method: "PATCH",
        body: JSON.stringify(payload),
      }),
    remove: (id: string) => request<void>(`/admin/workspaces/${id}`, { method: "DELETE" }),

    members: {
      list: (workspaceId: string) =>
        request<AdminMemberOut[]>(`/admin/workspaces/${workspaceId}/members`),
      add: (workspaceId: string, payload: { user_id: string; role?: Role }) =>
        request<AdminMemberOut>(`/admin/workspaces/${workspaceId}/members`, {
          method: "POST",
          body: JSON.stringify(payload),
        }),
      update: (workspaceId: string, userId: string, role: Role) =>
        request<AdminMemberOut>(`/admin/workspaces/${workspaceId}/members/${userId}`, {
          method: "PATCH",
          body: JSON.stringify({ role }),
        }),
      remove: (workspaceId: string, userId: string) =>
        request<void>(`/admin/workspaces/${workspaceId}/members/${userId}`, { method: "DELETE" }),
    },
  },
};

export const workspaces = {
  list: () => request<WorkspaceOut[]>("/workspaces"),
  create: (name: string) => request<WorkspaceOut>("/workspaces", { method: "POST", body: JSON.stringify({ name }) }),
  get: (id: string) => request<WorkspaceOut>(`/workspaces/${id}`),
  update: (id: string, name: string) =>
    request<WorkspaceOut>(`/workspaces/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),

  remove: (id: string) => request<void>(`/workspaces/${id}`, { method: "DELETE" }),

  members: {
    list: (workspaceId: string) => request<WorkspaceMember[]>(`/workspaces/${workspaceId}/members`),
    update: (workspaceId: string, memberUserId: string, role: Role) =>
      request<WorkspaceMember>(`/workspaces/${workspaceId}/members/${memberUserId}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
      }),
    remove: (workspaceId: string, memberUserId: string) =>
      request<void>(`/workspaces/${workspaceId}/members/${memberUserId}`, { method: "DELETE" }),
  },

  audit: (workspaceId: string, params: { limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<AuditLogListResponse>(`/workspaces/${workspaceId}/audit${qs ? `?${qs}` : ""}`);
  },
};

export const folders = {
  list: (workspaceId: string) => request<FolderOut[]>(`/workspaces/${workspaceId}/folders`),

  create: (workspaceId: string, name: string) =>
    request<FolderOut>(`/workspaces/${workspaceId}/folders`, { method: "POST", body: JSON.stringify({ name }) }),

  rename: (folderId: string, name: string) =>
    request<FolderOut>(`/folders/${folderId}`, { method: "PATCH", body: JSON.stringify({ name }) }),

  remove: (folderId: string) => request<void>(`/folders/${folderId}`, { method: "DELETE" }),
};

export const tags = {
  list: (workspaceId: string) => request<TagOut[]>(`/workspaces/${workspaceId}/tags`),

  create: (workspaceId: string, payload: { name: string; color?: string; scope?: TagScope }) =>
    request<TagOut>(`/workspaces/${workspaceId}/tags`, { method: "POST", body: JSON.stringify(payload) }),

  update: (tagId: string, payload: { name?: string; color?: string }) =>
    request<TagOut>(`/tags/${tagId}`, { method: "PATCH", body: JSON.stringify(payload) }),

  remove: (tagId: string) => request<void>(`/tags/${tagId}`, { method: "DELETE" }),
};

export const documents = {
  upload: (workspaceId: string, file: File, isPublic = false) => {
    const form = new FormData();
    form.append("file", file);
    if (isPublic) form.append("is_public", "true");
    return request<DocumentOut>(`/workspaces/${workspaceId}/documents`, { method: "POST", body: form });
  },

  listPublic: (params: { limit?: number; offset?: number } = {}) => {
    const query = new URLSearchParams();
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<PublicDocumentListResponse>(`/documents/public${qs ? `?${qs}` : ""}`);
  },

  setVisibility: (id: string, isPublic: boolean) =>
    request<DocumentOut>(`/documents/${id}/visibility`, {
      method: "PATCH",
      body: JSON.stringify({ is_public: isPublic }),
    }),

  list: (
    workspaceId: string,
    params: {
      status?: DocumentStatus;
      folderId?: string;
      tagId?: string;
      unfiled?: boolean;
      limit?: number;
      offset?: number;
    } = {},
  ) => {
    const query = new URLSearchParams();
    if (params.status) query.set("status", params.status);
    if (params.folderId) query.set("folder_id", params.folderId);
    if (params.tagId) query.set("tag_id", params.tagId);
    if (params.unfiled) query.set("unfiled", "true");
    if (params.limit !== undefined) query.set("limit", String(params.limit));
    if (params.offset !== undefined) query.set("offset", String(params.offset));
    const qs = query.toString();
    return request<DocumentListResponse>(`/workspaces/${workspaceId}/documents${qs ? `?${qs}` : ""}`);
  },

  get: (id: string) => request<DocumentOut>(`/documents/${id}`),

  setFolders: (id: string, folderIds: string[]) =>
    request<DocumentOut>(`/documents/${id}/folders`, { method: "PUT", body: JSON.stringify({ folder_ids: folderIds }) }),

  setTags: (id: string, tagIds: string[]) =>
    request<DocumentOut>(`/documents/${id}/tags`, { method: "PUT", body: JSON.stringify({ tag_ids: tagIds }) }),

  remove: (id: string) => request<void>(`/documents/${id}`, { method: "DELETE" }),

  pages: (id: string) => request<DocumentPageOut[]>(`/documents/${id}/pages`),

  page: (id: string, pageNumber: number) =>
    request<DocumentPageOut>(`/documents/${id}/pages/${pageNumber}`),

  file: (id: string) => request<Blob>(`/documents/${id}/file`, {}, true, true),

  fileBlob: async (id: string): Promise<string> => {
    const blob = await documents.file(id);
    return URL.createObjectURL(blob);
  },
};
