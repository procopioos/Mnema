"use client";

import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";

import { auth as authApi, tokenStore, workspaces } from "./api";
import type { Role, UserOut } from "./api";

type WorkspaceMeta = {
  workspaceId: string | null;
  role: Role | null;
};

type AuthState = {
  user: UserOut | null;
  workspaceId: string | null;
  role: Role | null;
  loading: boolean;
};

type AuthContextValue = AuthState & {
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, fullName: string) => Promise<void>;
  logout: () => void;
  refreshWorkspaceMeta: () => Promise<void>;
};

function resolveWorkspaceMeta(list: { id: string; role?: Role | null }[], preferredId: string | null): WorkspaceMeta {
  const current = (preferredId ? list.find((w) => w.id === preferredId) : undefined) ?? list[0] ?? null;
  return { workspaceId: current?.id ?? null, role: current?.role ?? null };
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null);
  const [workspaceId, setWorkspaceId] = useState<string | null>(null);
  const [role, setRole] = useState<Role | null>(null);
  const [loading, setLoading] = useState(true);
  const workspaceIdRef = useRef<string | null>(null);

  const applyMeta = useCallback((meta: WorkspaceMeta) => {
    workspaceIdRef.current = meta.workspaceId;
    setWorkspaceId(meta.workspaceId);
    setRole(meta.role);
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function bootstrap() {
      if (!tokenStore.getAccess()) {
        setLoading(false);
        return;
      }
      try {
        const me = await authApi.me();
        if (cancelled) return;
        setUser(me);
        const list = await workspaces.list();
        const meta = resolveWorkspaceMeta(list, null);
        if (cancelled) return;
        applyMeta(meta);
      } catch {
        if (!cancelled) tokenStore.clear();
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    bootstrap();
    return () => {
      cancelled = true;
    };
  }, [applyMeta]);

  const refreshWorkspaceMeta = useCallback(async () => {
    const list = await workspaces.list();
    applyMeta(resolveWorkspaceMeta(list, workspaceIdRef.current));
  }, [applyMeta]);

  const login = useCallback(
    async (email: string, password: string) => {
      const data = await authApi.login({ email, password });
      tokenStore.set(data.access_token, data.refresh_token);
      setUser(data.user);
      const list = await workspaces.list();
      applyMeta(resolveWorkspaceMeta(list, data.workspace_id ?? null));
    },
    [applyMeta],
  );

  const register = useCallback(
    async (email: string, password: string, fullName: string) => {
      const data = await authApi.register({ email, password, full_name: fullName });
      tokenStore.set(data.access_token, data.refresh_token);
      setUser(data.user);
      const list = await workspaces.list();
      applyMeta(resolveWorkspaceMeta(list, data.workspace_id ?? null));
    },
    [applyMeta],
  );

  const logout = useCallback(() => {
    workspaceIdRef.current = null;
    tokenStore.clear();
    setUser(null);
    setWorkspaceId(null);
    setRole(null);
  }, []);

  return (
    <AuthContext.Provider
      value={{ user, workspaceId, role, loading, login, register, logout, refreshWorkspaceMeta }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}