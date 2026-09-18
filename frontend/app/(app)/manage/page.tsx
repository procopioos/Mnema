"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Users, Settings2, Activity, Shield, BarChart3, UserCog, FileText, Globe } from "lucide-react";

import { RequireAuth } from "@/components/app-shell";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import type { TranslationKey } from "@/lib/translations/en";
import { canManage, canAdmin } from "@/lib/roles";

interface CardItem {
  icon: React.ReactNode;
  labelKey: TranslationKey;
  descKey: TranslationKey;
  onClick: () => void;
}

function CategorySection({ titleKey, items }: { titleKey: TranslationKey; items: CardItem[] }) {
  const { t } = useLanguage();
  return (
    <div className="space-y-3">
      <h2 className="text-sm font-semibold tracking-wide text-zinc-500 uppercase">
        {t(titleKey)}
      </h2>
      <div className="grid gap-3 sm:grid-cols-2">
        {items.map((item) => (
          <button
            key={item.labelKey}
            type="button"
            onClick={item.onClick}
            className="group rounded-xl border bg-card p-4 text-left shadow-xs transition-colors hover:bg-accent hover:text-accent-foreground"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 text-zinc-400 group-hover:text-accent-foreground">
                {item.icon}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium">{t(item.labelKey)}</p>
                <p className="mt-0.5 text-xs text-zinc-500 group-hover:text-zinc-400">
                  {t(item.descKey)}
                </p>
              </div>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export default function ManagePage() {
  const { user, role } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();

  const isSystemAdmin = !!user?.is_system_admin;
  const isAdmin = canAdmin(role);
  const isManager = canManage(role);

  useEffect(() => {
    if (!isSystemAdmin && !isAdmin && !isManager) router.replace("/");
  }, [isSystemAdmin, isAdmin, isManager, router]);

  if (!isSystemAdmin && !isAdmin && !isManager) return null;

  const openSettings = (tab: string) => router.push(`/?settings=${tab}`);

  const workspaceItems: CardItem[] = [];
  if (isAdmin) {
    workspaceItems.push(
      {
        icon: <Users className="size-4" />,
        labelKey: "manage.workspace.team",
        descKey: "manage.workspace.teamDesc",
        onClick: () => openSettings("team"),
      },
      {
        icon: <Settings2 className="size-4" />,
        labelKey: "manage.workspace.settings",
        descKey: "manage.workspace.settingsDesc",
        onClick: () => openSettings("workspace"),
      }
    );
  }

  const activityItems: CardItem[] = [];
  if (isManager) {
    activityItems.push({
      icon: <Activity className="size-4" />,
      labelKey: "manage.activity.log",
      descKey: "manage.activity.logDesc",
      onClick: () => router.push("/activity"),
    });
  }

  const adminItems: CardItem[] = [];
  if (isSystemAdmin) {
    adminItems.push(
      {
        icon: <BarChart3 className="size-4" />,
        labelKey: "manage.admin.overview",
        descKey: "manage.admin.overviewDesc",
        onClick: () => router.push("/admin?tab=overview"),
      },
      {
        icon: <UserCog className="size-4" />,
        labelKey: "manage.admin.users",
        descKey: "manage.admin.usersDesc",
        onClick: () => router.push("/admin?tab=users"),
      },
      {
        icon: <FileText className="size-4" />,
        labelKey: "manage.admin.workspaces",
        descKey: "manage.admin.workspacesDesc",
        onClick: () => router.push("/admin?tab=workspaces"),
      },
      {
        icon: <Shield className="size-4" />,
        labelKey: "manage.admin.systemActivity",
        descKey: "manage.admin.systemActivityDesc",
        onClick: () => router.push("/activity"),
      }
    );
  }

  const accountItems: CardItem[] = [
    {
      icon: <Globe className="size-4" />,
      labelKey: "manage.account.profile",
      descKey: "manage.account.profileDesc",
      onClick: () => openSettings("general"),
    },
  ];

  return (
    <RequireAuth>
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{t("manage.title")}</h1>
          <p className="mt-1 text-sm text-zinc-500">{t("manage.description")}</p>
        </div>

        {workspaceItems.length > 0 && (
          <CategorySection titleKey="manage.workspace.title" items={workspaceItems} />
        )}
        {activityItems.length > 0 && (
          <CategorySection titleKey="manage.activity.title" items={activityItems} />
        )}
        {adminItems.length > 0 && (
          <CategorySection titleKey="manage.admin.title" items={adminItems} />
        )}
        <CategorySection titleKey="manage.account.title" items={accountItems} />
      </div>
    </RequireAuth>
  );
}