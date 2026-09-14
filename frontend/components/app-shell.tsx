"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { ChevronDown, LogOut, LayoutDashboard, Settings, Shield } from "lucide-react";

import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { canAdmin, canManage } from "@/lib/roles";
import { Button } from "@/components/ui/button";
import { Sparkles, WavyDivider } from "@/components/doodles";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { SettingsDialog, type Tab } from "@/components/settings-dialog";

export function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) router.replace("/login");
  }, [loading, user, router]);

  if (loading || !user) return null;
  return <>{children}</>;
}

export function RequireAdmin({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && user && !user.is_system_admin) router.replace("/");
  }, [loading, user, router]);

  if (loading || !user || !user.is_system_admin) return null;
  return <>{children}</>;
}

function SettingsLauncher() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const { role, user } = useAuth();

  const requested = searchParams.get("settings");
  const isSystemAdmin = !!user?.is_system_admin;
  const isAdmin = canAdmin(role);
  const isManager = canManage(role);

  const valid: Tab[] = ["general", "workspace", "team", "activity", "advanced"];
  const desired = requested as Tab;
  const allowed =
    requested != null &&
    valid.includes(desired) &&
    ((desired === "workspace" || desired === "team"
      ? isAdmin
      : false) ||
      (desired === "activity" ? isManager : false) ||
      (desired === "advanced" ? isSystemAdmin : false) ||
      desired === "general");

  function onOpenChange(next: boolean) {
    if (!next && requested) {
      const params = new URLSearchParams(searchParams.toString());
      params.delete("settings");
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : "/");
    }
  }

  return (
    <SettingsDialog
      open={allowed}
      onOpenChange={onOpenChange}
      initialTab={allowed ? (desired as Tab) : "general"}
      key={allowed ? (desired as Tab) : "general"}
    />
  );
}

export function AppHeader() {
  const { user, role, logout } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();
  const [settingsOpen, setSettingsOpen] = useState(false);

  const showManage = canManage(role) || !!user?.is_system_admin;

  function onLogout() {
    logout();
    router.replace("/login");
  }

  return (
    <header className="sticky top-0 z-50 border-b bg-background/70 backdrop-blur-xl dark:bg-background/70">
      <WavyDivider className="pointer-events-none absolute inset-x-0 top-full h-3 w-full text-foreground/[0.04]" />
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <nav className="flex items-center gap-6">
          <Link href="/" className="flex items-center gap-1.5 text-base font-semibold tracking-tight">
            <Sparkles className="size-4 text-foreground/40" />
            Mnema
          </Link>
          <Link href="/" className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
            {t("nav.dashboard")}
          </Link>
          <Link href="/documents" className="text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
            {t("nav.documents")}
          </Link>
          {user?.is_system_admin && (
            <Link href="/admin" className="flex items-center gap-1 text-sm text-zinc-600 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100">
              <Shield className="size-3.5" />
              {t("nav.admin")}
            </Link>
          )}
        </nav>
        <div className="flex items-center gap-3">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-1.5">
                <span className="hidden max-w-48 truncate text-sm text-zinc-600 dark:text-zinc-400 sm:inline">
                  {user?.full_name}
                </span>
                <ChevronDown className="h-4 w-4 text-zinc-500" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="min-w-64">
              <DropdownMenuLabel>
                <p className="text-sm font-semibold">{user?.full_name}</p>
                <p className="whitespace-normal break-words text-xs text-muted-foreground">{user?.email}</p>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => setSettingsOpen(true)}>
                <Settings />
                {t("nav.settings")}
              </DropdownMenuItem>
              {showManage && (
                <DropdownMenuItem onSelect={() => router.push("/manage")}>
                  <LayoutDashboard />
                  {t("nav.manage")}
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem variant="destructive" className="bg-destructive/10" onSelect={onLogout}>
                <LogOut />
                {t("nav.logOut")}
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
      <SettingsDialog open={settingsOpen} onOpenChange={setSettingsOpen} />
      <Suspense fallback={null}>
        <SettingsLauncher />
      </Suspense>
    </header>
  );
}