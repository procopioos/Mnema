"use client";

import { useEffect, useState } from "react";
import { ChevronLeft, ChevronRight, FileText } from "lucide-react";
import Link from "next/link";

import { admin, workspaces } from "@/lib/api";
import type { AuditLogListResponse } from "@/lib/api";
import { AUDIT_ACTION_LABEL_KEY, formatAuditTime } from "@/lib/audit";
import { useLanguage } from "@/lib/i18n";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";

const PAGE_SIZE = 20;

export function AuditView({
  workspaceId,
  adminMode = false,
  filterWorkspaceId,
}: {
  workspaceId?: string;
  adminMode?: boolean;
  filterWorkspaceId?: string;
}) {
  const { t } = useLanguage();
  const [data, setData] = useState<AuditLogListResponse | null>(null);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = adminMode
          ? await admin.audit({ workspaceId: filterWorkspaceId, limit: PAGE_SIZE, offset })
          : await workspaces.audit(workspaceId ?? "", { limit: PAGE_SIZE, offset });
        if (!cancelled) {
          setData(res);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : t("settings.activityFailed"));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [adminMode, filterWorkspaceId, offset, t, workspaceId]);

  const items = data?.items ?? [];
  const hasNext = data != null && offset + PAGE_SIZE < data.total;

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertDescription>{error}</AlertDescription>
      </Alert>
    );
  }

  if (loading) {
    return <p className="text-sm text-zinc-400">{t("settings.loading")}</p>;
  }

  if (items.length === 0) {
    return <p className="text-sm text-zinc-400">{t("settings.noActivity")}</p>;
  }

  return (
    <div className="space-y-2">
      <ul className="space-y-1.5">
        {items.map((item) => (
          <li key={item.id} className="flex items-start justify-between gap-3 rounded-md border px-3 py-2">
            <div className="min-w-0">
              <p className="text-sm font-medium">
                {t(AUDIT_ACTION_LABEL_KEY[item.action])}
                <span className="ml-1.5 text-xs font-normal text-zinc-400">
                  {item.user_full_name ?? item.user_email ?? ""}
                </span>
              </p>
              {item.document_filename && (
                <p className="flex items-center gap-1 text-xs text-zinc-500">
                  {item.document_id ? (
                    <Link href={`/documents/${item.document_id}`} className="flex items-center gap-1 hover:underline">
                      <FileText className="h-3 w-3" />
                      {item.document_filename}
                    </Link>
                  ) : (
                    <>
                      <FileText className="h-3 w-3" />
                      {item.document_filename}
                    </>
                  )}
                </p>
              )}
            </div>
            <time className="shrink-0 text-xs whitespace-nowrap text-zinc-400">
              {formatAuditTime(item.created_at)}
            </time>
          </li>
        ))}
      </ul>
      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          disabled={offset === 0}
          onClick={() => setOffset((o) => Math.max(0, o - PAGE_SIZE))}
        >
          <ChevronLeft className="mr-1 h-3.5 w-3.5" />
          {t("audit.previous")}
        </Button>
        <Button variant="outline" size="sm" disabled={!hasNext} onClick={() => setOffset((o) => o + PAGE_SIZE)}>
          {t("audit.next")}
          <ChevronRight className="ml-1 h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}