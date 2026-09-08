"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Activity, AlertTriangle, Save, Trash2, Users } from "lucide-react";

import { admin, workspaces } from "@/lib/api";
import type { Role, WorkspaceMember } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";
import { useLanguage, LANGUAGES } from "@/lib/i18n";
import { canAdmin, canManage, ROLE_LABEL_KEY } from "@/lib/roles";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { AuditView } from "@/components/audit-view";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RoleBadge } from "@/components/role-badge";

const SELECT_CLASSES =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none";

const ROLES: Role[] = ["owner", "admin", "manager", "employee"];

export function SettingsDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const router = useRouter();
  const { workspaceId, role, user, logout, refreshWorkspaceMeta } = useAuth();
  const { language, setLanguage, t } = useLanguage();
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [typed, setTyped] = useState("");
  const [resetting, setResetting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const isAdmin = canAdmin(role);

  const [workspaceName, setWorkspaceName] = useState("");
  const [savingWorkspace, setSavingWorkspace] = useState(false);
  const [deleteWsOpen, setDeleteWsOpen] = useState(false);
  const [wsTyped, setWsTyped] = useState("");
  const [deletingWorkspace, setDeletingWorkspace] = useState(false);

  const [members, setMembers] = useState<WorkspaceMember[] | null>(null);
  const [membersError, setMembersError] = useState<string | null>(null);
  const [busyMember, setBusyMember] = useState<string | null>(null);

  useEffect(() => {
    if (!open || !isAdmin || !workspaceId) return;
    let cancelled = false;
    (async () => {
      try {
        const ws = await workspaces.get(workspaceId);
        if (!cancelled) setWorkspaceName(ws.name);
      } catch (err) {
        if (!cancelled) setError(err instanceof Error ? err.message : t("settings.failedToLoad"));
      }
      try {
        const list = await workspaces.members.list(workspaceId);
        if (!cancelled) setMembers(list);
      } catch (err) {
        if (!cancelled) setMembersError(err instanceof Error ? err.message : t("settings.membersFailed"));
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [open, isAdmin, workspaceId, t]);

  async function onReset() {
    if (typed !== "RESET") return;
    setResetting(true);
    setError(null);
    try {
      await admin.reset();
      logout();
      setConfirmOpen(false);
      setTyped("");
      onOpenChange(false);
      router.replace("/register");
    } catch (err) {
      setError(err instanceof Error ? err.message : t("settings.resetFailed"));
      setResetting(false);
    }
  }

  async function onRenameWorkspace() {
    if (!workspaceId || !workspaceName.trim()) return;
    setSavingWorkspace(true);
    setError(null);
    try {
      await workspaces.update(workspaceId, workspaceName.trim());
      await refreshWorkspaceMeta();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("settings.updateFailed"));
    } finally {
      setSavingWorkspace(false);
    }
  }

  async function onDeleteWorkspace() {
    if (!workspaceId || wsTyped !== "DELETE") return;
    setDeletingWorkspace(true);
    setError(null);
    try {
      await workspaces.remove(workspaceId);
      setDeleteWsOpen(false);
      setWsTyped("");
      onOpenChange(false);
      await refreshWorkspaceMeta();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("settings.updateFailed"));
      setDeletingWorkspace(false);
    }
  }

  async function changeMemberRole(member: WorkspaceMember, nextRole: Role) {
    if (!workspaceId || member.role === "owner") return;
    setBusyMember(member.user_id);
    setMembersError(null);
    try {
      const updated = await workspaces.members.update(workspaceId, member.user_id, nextRole);
      setMembers((prev) => (prev ? prev.map((m) => (m.user_id === updated.user_id ? updated : m)) : prev));
      await refreshWorkspaceMeta();
    } catch (err) {
      setMembersError(err instanceof Error ? err.message : t("settings.updateFailed"));
    } finally {
      setBusyMember(null);
    }
  }

  async function removeMember(member: WorkspaceMember) {
    if (!workspaceId || member.role === "owner") return;
    if (!window.confirm(t("settings.removeMemberConfirm"))) return;
    setBusyMember(member.user_id);
    setMembersError(null);
    try {
      await workspaces.members.remove(workspaceId, member.user_id);
      setMembers((prev) => (prev ? prev.filter((m) => m.user_id !== member.user_id) : prev));
      await refreshWorkspaceMeta();
    } catch (err) {
      setMembersError(err instanceof Error ? err.message : t("settings.updateFailed"));
    } finally {
      setBusyMember(null);
    }
  }

  return (
    <>
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl!">
          <DialogHeader>
            <DialogTitle>{t("settings.title")}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2 rounded-lg border p-4">
              <p className="text-sm text-zinc-500">{t("settings.languageDescription")}</p>
              <div className="space-y-1.5">
                <Label htmlFor="settings-language">{t("settings.language")}</Label>
                <select
                  id="settings-language"
                  value={language}
                  onChange={(e) => setLanguage(e.target.value as typeof language)}
                  className={SELECT_CLASSES}
                >
                  {LANGUAGES.map((lang) => (
                    <option key={lang} value={lang}>
                      {t(lang === "en" ? "languages.en" : "languages.it")}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            {isAdmin && workspaceId && (
              <>
                <div className="space-y-3 rounded-lg border p-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Save className="h-4 w-4 text-zinc-500" />
                    {t("settings.workspace")}
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="settings-workspace-name">{t("settings.workspaceName")}</Label>
                    <Input
                      id="settings-workspace-name"
                      value={workspaceName}
                      onChange={(e) => setWorkspaceName(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" && !savingWorkspace) onRenameWorkspace();
                      }}
                    />
                  </div>
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={savingWorkspace || !workspaceName.trim()}
                    onClick={onRenameWorkspace}
                  >
                    {savingWorkspace ? t("settings.saving") : t("settings.saveChanges")}
                  </Button>
                  <Button
                    variant="destructive"
                    className="ml-2 bg-destructive/10 text-destructive hover:bg-destructive/20"
                    size="sm"
                    onClick={() => {
                      setWsTyped("");
                      setDeleteWsOpen(true);
                    }}
                  >
                    <Trash2 className="mr-1.5 h-3.5 w-3.5" />
                    {t("settings.deleteWorkspace")}
                  </Button>
                </div>

                <div className="space-y-3 rounded-lg border p-4">
                  <div className="flex items-center gap-2 text-sm font-medium">
                    <Users className="h-4 w-4 text-zinc-500" />
                    {t("settings.team")}
                  </div>
                  {membersError && (
                    <Alert variant="destructive">
                      <AlertDescription>{membersError}</AlertDescription>
                    </Alert>
                  )}
                  {members === null ? (
                    <p className="text-sm text-zinc-400">{t("settings.loading")}</p>
                  ) : members.length === 0 ? (
                    <p className="text-sm text-zinc-400">{t("settings.noMembers")}</p>
                  ) : (
                    <ul className="space-y-2">
                      {members.map((member) => (
                        <li
                          key={member.user_id}
                          className="flex items-center justify-between gap-3 rounded-md border px-3 py-2"
                        >
                          <div className="min-w-0">
                            <p className="truncate text-sm font-medium">
                              {member.full_name}
                              <span className="ml-1.5 text-xs font-normal text-zinc-400">{member.email}</span>
                            </p>
                            <RoleBadge role={member.role} />
                          </div>
                          <div className="flex items-center gap-2">
                            <select
                              aria-label={t("settings.memberRole")}
                              value={member.role}
                              disabled={member.role === "owner" || busyMember === member.user_id}
                              onChange={(e) => changeMemberRole(member, e.target.value as Role)}
                              className="h-9 w-28 rounded-md border border-input bg-transparent px-2 py-1 text-sm disabled:opacity-60"
                            >
                              {ROLES.map((r) => (
                                <option key={r} value={r} disabled={r === "owner" || r === member.role}>
                                  {t(ROLE_LABEL_KEY[r])}
                                </option>
                              ))}
                            </select>
                            <Button
                              variant="ghost"
                              size="icon"
                              aria-label={t("settings.removeMember")}
                              disabled={member.role === "owner" || busyMember === member.user_id}
                              onClick={() => removeMember(member)}
                            >
                              <Trash2 className="h-4 w-4" />
                            </Button>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </>
            )}

            {canManage(role) && workspaceId && (
              <div className="space-y-3 rounded-lg border p-4">
                <div className="flex items-center gap-2 text-sm font-medium">
                  <Activity className="h-4 w-4 text-zinc-500" />
                  {t("settings.activity")}
                </div>
                <p className="text-sm text-zinc-500">{t("settings.activityDescription")}</p>
                <AuditView workspaceId={workspaceId} />
              </div>
            )}

            {error && (
              <Alert variant="destructive">
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            {user?.is_system_admin && (
              <div className="space-y-2 rounded-lg border border-red-200 p-4 dark:border-red-900">
                <div className="flex items-center gap-2 text-sm font-medium text-red-600 dark:text-red-400">
                  <AlertTriangle className="h-4 w-4" />
                  {t("settings.dangerZone")}
                </div>
                <p className="text-sm text-zinc-500">{t("settings.resetDescription")}</p>
                <Button variant="destructive" className="bg-destructive/10 text-destructive hover:bg-destructive/20" onClick={() => { setTyped(""); setConfirmOpen(true); }}>
                  {t("settings.resetApp")}
                </Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={confirmOpen} onOpenChange={(open) => !open && !resetting && setConfirmOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600 dark:text-red-400">{t("settings.resetTitle")}</DialogTitle>
            <DialogDescription>
              {t("settings.resetConfirmDescription")}
            </DialogDescription>
          </DialogHeader>
          <Input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="RESET"
            aria-label={t("settings.resetConfirmDescription")}
          />
          <DialogFooter>
            <Button variant="outline" disabled={resetting} onClick={() => setConfirmOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" disabled={typed !== "RESET" || resetting} onClick={onReset}>
              {resetting ? t("settings.resetting") : t("settings.reset")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={deleteWsOpen} onOpenChange={(open) => !open && !deletingWorkspace && setDeleteWsOpen(false)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-red-600 dark:text-red-400">{t("settings.deleteWorkspaceTitle")}</DialogTitle>
            <DialogDescription>
              {t("settings.deleteWorkspaceDescription")}
            </DialogDescription>
          </DialogHeader>
          <Input
            value={wsTyped}
            onChange={(e) => setWsTyped(e.target.value)}
            placeholder="DELETE"
            aria-label={t("settings.deleteWorkspaceDescription")}
          />
          <DialogFooter>
            <Button variant="outline" disabled={deletingWorkspace} onClick={() => setDeleteWsOpen(false)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" disabled={wsTyped !== "DELETE" || deletingWorkspace} onClick={onDeleteWorkspace}>
              {deletingWorkspace ? t("settings.deletingWorkspace") : t("settings.deleteWorkspace")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}