"use client";

import { Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";

import { RequireAuth } from "@/components/app-shell";
import { ActivityPanel } from "@/components/admin/activity-panel";
import { AuditView } from "@/components/audit-view";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { canManage } from "@/lib/roles";

function ActivityContent() {
  const { user, role, workspaceId } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();
  const searchParams = useSearchParams();

  const isSystemAdmin = !!user?.is_system_admin;
  const isManager = canManage(role);

  const override = searchParams.get("workspace") ?? undefined;
  const effectiveWorkspaceId = override ?? workspaceId ?? undefined;

  if (!isSystemAdmin && !isManager) {
    router.replace("/");
    return null;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-semibold tracking-tight">{t("activity.title")}</h1>
        <p className="mt-1 text-sm text-zinc-500">
          {t(isSystemAdmin ? "activity.systemDescription" : "activity.description")}
        </p>
      </div>

      {isSystemAdmin ? (
        <ActivityPanel />
      ) : effectiveWorkspaceId ? (
        <AuditView key={effectiveWorkspaceId} workspaceId={effectiveWorkspaceId} />
      ) : null}
    </div>
  );
}

export default function ActivityPage() {
  return (
    <RequireAuth>
      <Suspense>
        <ActivityContent />
      </Suspense>
    </RequireAuth>
  );
}
