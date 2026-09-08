"use client";

import { useEffect, useState } from "react";
import { FileText, FolderOpen, HardDrive, Users } from "lucide-react";

import { admin } from "@/lib/api";
import type { AdminStatsOut, AdminWorkspaceOut } from "@/lib/api";
import { formatStorage } from "@/lib/admin";
import { formatBytes } from "@/components/document-card";
import { useLanguage } from "@/lib/i18n";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";

function StatCard({
  icon: Icon,
  label,
  value,
  hint,
}: {
  icon: typeof Users;
  label: string;
  value: string;
  hint?: string;
}) {
  return (
    <Card className="tilt-neg tilted transition-shadow hover:shadow-lg">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-500">
          <span className="flex size-6 items-center justify-center rounded-md bg-muted">
            <Icon className="h-3.5 w-3.5" />
          </span>
          {label}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-4xl font-semibold tabular-nums tracking-tight">{value}</div>
        {hint && <p className="mt-1 text-xs text-zinc-400">{hint}</p>}
      </CardContent>
    </Card>
  );
}

export function Overview() {
  const { t } = useLanguage();
  const [stats, setStats] = useState<AdminStatsOut | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    admin
      .stats()
      .then((s) => {
        if (!cancelled) setStats(s);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : t("admin.failedToLoad"));
      });
    return () => {
      cancelled = true;
    };
  }, [t]);

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (!stats) {
    return (
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Skeleton className="h-32 w-full rounded-display" />
        <Skeleton className="h-32 w-full rounded-display" />
        <Skeleton className="h-32 w-full rounded-display" />
        <Skeleton className="h-32 w-full rounded-display" />
      </div>
    );
  }

  const d = stats.documents ?? { total: 0, pending: 0, processing: 0, ready: 0, failed: 0 };
  const usage = stats.workspaces_usage ?? [];
  const statusHint = [
    d.ready > 0 ? `${t("status.ready")} ${d.ready}` : "",
    d.processing > 0 ? `${t("status.processing")} ${d.processing}` : "",
    d.pending > 0 ? `${t("status.pending")} ${d.pending}` : "",
    d.failed > 0 ? `${t("status.failed")} ${d.failed}` : "",
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard icon={Users} label={t("admin.statUsers")} value={String(stats.users)} />
        <StatCard icon={FolderOpen} label={t("admin.statWorkspaces")} value={String(stats.workspaces)} />
        <StatCard
          icon={FileText}
          label={t("admin.statDocuments")}
          value={String(d.total)}
          hint={statusHint || undefined}
        />
        <StatCard icon={HardDrive} label={t("admin.statStorage")} value={formatStorage(stats.storage_bytes)} />
      </div>

      <Card className="transition-shadow hover:shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-500">
            <span className="flex size-6 items-center justify-center rounded-md bg-muted">
              <FolderOpen className="h-3.5 w-3.5" />
            </span>
            {t("admin.usageByWorkspace")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {stats.workspaces_usage?.length === 0 ? (
            <p className="text-sm text-zinc-400">{t("admin.noWorkspaces")}</p>
          ) : (
            usage.map((ws: AdminWorkspaceOut) => (
              <div
                key={ws.id}
                className="flex items-center justify-between gap-3 rounded-lg border px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{ws.name}</p>
                  <p className="text-xs text-zinc-500">
                    {ws.member_count} {t("admin.members")} · {ws.document_count} {t("documents.documents")} ·{" "}
                    {formatBytes(ws.storage_bytes ?? 0)}
                  </p>
                </div>
                <div className="flex shrink-0 items-center gap-3 text-xs">
                  {ws.max_documents !== null || ws.max_storage_bytes !== null ? (
                    <span className="text-zinc-400">
                      {ws.max_documents !== null ? ws.max_documents : ""}
                      {ws.max_documents !== null && ws.max_storage_bytes !== null ? " · " : ""}
                      {ws.max_storage_bytes !== null ? formatStorage(ws.max_storage_bytes ?? 0) : ""}
                    </span>
                  ) : (
                    <span className="text-zinc-400">{t("admin.defaultQuota")}</span>
                  )}
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}