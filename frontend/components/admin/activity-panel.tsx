"use client";

import { useEffect, useState } from "react";

import { AdminWorkspaceOut, admin } from "@/lib/api";
import { AuditView } from "@/components/audit-view";
import { useLanguage } from "@/lib/i18n";

const SELECT_CLASSES =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none";

export function ActivityPanel() {
  const { t } = useLanguage();
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceOut[]>([]);
  const [filter, setFilter] = useState<string | undefined>(undefined);

  useEffect(() => {
    admin.workspaces
      .list()
      .then(setWorkspaces)
      .catch(() => setWorkspaces([]));
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <span className="text-sm text-zinc-500">{t("admin.activityFor")}</span>
        <select
          value={filter ?? ""}
          onChange={(e) => setFilter(e.target.value || undefined)}
          className={`${SELECT_CLASSES} w-64`}
        >
          <option value="">{t("admin.allWorkspaces")}</option>
          {workspaces.map((w) => (
            <option key={w.id} value={w.id}>
              {w.name}
            </option>
          ))}
        </select>
      </div>
      <AuditView key={filter ?? "all"} adminMode filterWorkspaceId={filter} />
    </div>
  );
}