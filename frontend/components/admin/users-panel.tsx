"use client";

import { useEffect, useState } from "react";
import { Search, Shield, Crown } from "lucide-react";

import { admin } from "@/lib/api";
import type { AdminUserOut } from "@/lib/api";
import { useLanguage } from "@/lib/i18n";
import { formatDate } from "@/components/document-card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";

export function UsersPanel() {
  const { t, language } = useLanguage();
  const [users, setUsers] = useState<AdminUserOut[] | null>(null);
  const [query, setQuery] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    admin
      .users(query)
      .then((list) => {
        if (!cancelled) {
          setUsers(list);
          setError(null);
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : t("admin.failedToLoad"));
      });
    return () => {
      cancelled = true;
    };
  }, [query, t]);

  async function toggleAdmin(user: AdminUserOut) {
    setBusy(user.id);
    setError(null);
    try {
      await admin.updateUser(user.id, { is_system_admin: !user.is_system_admin });
      setUsers(
        (prev) =>
          prev?.map((u) => (u.id === user.id ? { ...u, is_system_admin: !user.is_system_admin } : u)) ??
          prev,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="space-y-4">
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className="relative">
        <Search className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-zinc-400" />
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={t("admin.searchUsers")}
          className="pl-9"
        />
      </div>

      {users === null ? (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
          <Skeleton className="h-12 w-full rounded-lg" />
        </div>
      ) : users.length === 0 ? (
        <p className="text-sm text-zinc-400">{t("admin.noUsers")}</p>
      ) : (
        <ul className="space-y-1.5">
          {users.map((user) => (
            <li
              key={user.id}
              className="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
            >
              <div className="min-w-0">
                <p className="flex flex-wrap items-center gap-1.5 text-sm font-medium">
                  {user.full_name || "—"}
                  {user.is_root && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-red-500/40 bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-600 dark:text-red-300">
                      <Crown className="size-3" />
                      {t("admin.rootAdmin")}
                    </span>
                  )}
                  {user.is_system_admin && !user.is_root && (
                    <span className="inline-flex items-center gap-1 rounded-full border border-zinc-500/40 bg-zinc-500/10 px-2 py-0.5 text-xs font-medium">
                      <Shield className="size-3" />
                      {t("admin.systemAdmin")}
                    </span>
                  )}
                </p>
                <p className="truncate text-xs text-zinc-500">
                  {user.email} · {formatDate(user.created_at, language)}
                </p>
              </div>
              {!user.is_root && (
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy === user.id}
                  onClick={() => toggleAdmin(user)}
                >
                  {busy === user.id
                    ? "…"
                    : user.is_system_admin
                      ? t("admin.demoteAdmin")
                      : t("admin.promoteAdmin")}
                </Button>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}