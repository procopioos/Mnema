"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { RequireAdmin } from "@/components/app-shell";
import { ActivityPanel } from "@/components/admin/activity-panel";
import { Overview } from "@/components/admin/overview";
import { UsersPanel } from "@/components/admin/users-panel";
import { WorkspacesPanel } from "@/components/admin/workspaces-panel";
import { useLanguage } from "@/lib/i18n";
import type { TranslationKey } from "@/lib/i18n";

export type AdminTab = "overview" | "users" | "workspaces" | "activity";

const TABS: { id: AdminTab; key: TranslationKey }[] = [
  { id: "overview", key: "admin.overview" },
  { id: "users", key: "admin.users" },
  { id: "workspaces", key: "admin.workspaces" },
  { id: "activity", key: "admin.activity" },
];

const TAB_IDS = new Set<string>(TABS.map((tb) => tb.id));

function AdminContent() {
  const { t } = useLanguage();
  const router = useRouter();
  const searchParams = useSearchParams();
  const requested = searchParams.get("tab");
  const tab: AdminTab = TAB_IDS.has(requested ?? "") ? (requested as AdminTab) : "overview";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{t("admin.title")}</h1>
        <p className="mt-1 text-sm text-zinc-500">{t("admin.description")}</p>
      </div>

      <div
        role="tablist"
        aria-label={t("admin.title")}
        className="flex w-fit items-center gap-0.5 rounded-lg border bg-card p-0.5 shadow-xs"
      >
        {TABS.map((tb) => (
          <button
            key={tb.id}
            type="button"
            role="tab"
            aria-selected={tab === tb.id}
            onClick={() => router.push(`/admin?tab=${tb.id}`)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
              tab === tb.id
                ? "bg-muted text-foreground"
                : "text-zinc-400 hover:text-foreground"
            }`}
          >
            {t(tb.key)}
          </button>
        ))}
      </div>

      {tab === "overview" && <Overview />}
      {tab === "users" && <UsersPanel />}
      {tab === "workspaces" && <WorkspacesPanel />}
      {tab === "activity" && <ActivityPanel />}
    </div>
  );
}

export default function AdminPage() {
  return (
    <RequireAdmin>
      <Suspense fallback={null}>
        <AdminContent />
      </Suspense>
    </RequireAdmin>
  );
}