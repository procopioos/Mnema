"use client";

import { memo } from "react";

import { Badge } from "@/components/ui/badge";
import { useLanguage } from "@/lib/i18n";
import { Confetti } from "@/components/doodles";
import type { DocumentStatus } from "@/lib/api";

const STYLES: Record<DocumentStatus, string> = {
  pending: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  processing: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
  ready: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
  failed: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
};

const LABELS: Record<DocumentStatus, "status.pending" | "status.processing" | "status.ready" | "status.failed"> = {
  pending: "status.pending",
  processing: "status.processing",
  ready: "status.ready",
  failed: "status.failed",
};

export const StatusBadge = memo(function StatusBadge({ status }: { status: DocumentStatus }) {
  const { t } = useLanguage();
  return (
    <span className="inline-flex items-center gap-1">
      <Badge className={`font-mono shadow-xs ${status === "processing" ? "badge-pulse" : ""} ${STYLES[status]}`}>
        {t(LABELS[status])}
      </Badge>
      {status === "ready" && <Confetti className="text-foreground/25" size={22} />}
    </span>
  );
});