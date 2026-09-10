"use client";

import { useEffect, useState } from "react";
import { Copy, Pencil, Plus, RefreshCw, Settings2, Trash2, Users } from "lucide-react";

import { admin } from "@/lib/api";
import type { AdminMemberOut, AdminUserOut, AdminWorkspaceOut, Role } from "@/lib/api";
import { formatStorage } from "@/lib/admin";
import { formatBytes, formatDate } from "@/components/document-card";
import { RoleBadge } from "@/components/role-badge";
import { ROLE_LABEL_KEY } from "@/lib/roles";
import { useLanguage } from "@/lib/i18n";
import { Alert, AlertDescription } from "@/components/ui/alert";
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
import { Skeleton } from "@/components/ui/skeleton";

const SELECT_CLASSES =
  "h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:ring-1 focus-visible:ring-ring focus-visible:outline-none";

const ROLES: Role[] = ["owner", "admin", "manager", "employee"];

type DialogKind = "create" | "rename" | "quota" | "members" | "delete";

export function WorkspacesPanel() {
  const { t, language } = useLanguage();
  const [workspaces, setWorkspaces] = useState<AdminWorkspaceOut[] | null>(null);
  const [users, setUsers] = useState<AdminUserOut[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [dialog, setDialog] = useState<{ kind: DialogKind; ws: AdminWorkspaceOut | null } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  function load() {
    Promise.all([admin.workspaces.list(), admin.users()])
      .then(([ws, us]) => {
        setWorkspaces(ws);
        setUsers(us);
        setError(null);
      })
      .catch((err) => setError(err instanceof Error ? err.message : t("admin.failedToLoad")));
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function copyCode(id: string, code: string) {
    try {
      await navigator.clipboard.writeText(code);
      setCopiedId(id);
      window.setTimeout(() => setCopiedId(null), 1500);
    } catch {
      // clipboard unavailable; ignore
    }
  }

  async function regenerateCode(target: AdminWorkspaceOut) {
    if (!window.confirm(`${t("admin.regenerateCode")} — ${target.name}?`)) return;
    setBusy(target.id);
    setError(null);
    try {
      await admin.workspaces.regenerateCode(target.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function deleteWorkspace(target: AdminWorkspaceOut) {
    setBusy(target.id);
    setError(null);
    try {
      await admin.workspaces.remove(target.id);
      setDialog(null);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.deleteFailed"));
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

      <div className="flex justify-end">
        <Button onClick={() => setDialog({ kind: "create", ws: null })}>
          <Plus className="mr-2 h-4 w-4" />
          {t("admin.createWorkspace")}
        </Button>
      </div>

      {workspaces === null ? (
        <div className="space-y-2">
          <Skeleton className="h-14 w-full rounded-lg" />
          <Skeleton className="h-14 w-full rounded-lg" />
          <Skeleton className="h-14 w-full rounded-lg" />
        </div>
      ) : workspaces.length === 0 ? (
        <p className="text-sm text-zinc-400">{t("admin.noWorkspaces")}</p>
      ) : (
        <ul className="space-y-1.5">
          {workspaces.map((ws) => (
            <li key={ws.id} className="rounded-md border px-3 py-2">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{ws.name}</p>
                  <p className="mt-0.5 text-xs text-zinc-500">
                    {ws.member_count} {t("admin.members")} · {ws.document_count}{" "}
                    {t("documents.documents")} · {formatBytes(ws.storage_bytes ?? 0)}
                  </p>
                  {ws.invite_code && (
                    <div className="mt-1 flex items-center gap-1.5">
                      <code className="rounded border bg-muted px-1.5 py-0.5 font-mono text-xs tracking-widest">
                        {ws.invite_code}
                      </code>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="h-6 px-1.5 text-xs"
                        onClick={() => copyCode(ws.id, ws.invite_code!)}
                      >
                        <Copy className="h-3 w-3" />
                        {copiedId === ws.id ? t("common.copied") : t("common.copy")}
                      </Button>
                    </div>
                  )}
                </div>
                <div className="flex shrink-0 items-center gap-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    title={t("admin.regenerateCode")}
                    disabled={busy === ws.id}
                    onClick={() => regenerateCode(ws)}
                  >
                    <RefreshCw className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">{t("admin.regenerateCode")}</span>
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDialog({ kind: "rename", ws })}>
                    <Pencil className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">{t("admin.rename")}</span>
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDialog({ kind: "quota", ws })}>
                    <Settings2 className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">{t("admin.editQuota")}</span>
                  </Button>
                  <Button variant="ghost" size="sm" onClick={() => setDialog({ kind: "members", ws })}>
                    <Users className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">{t("admin.manageMembers")}</span>
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:bg-red-500/10 hover:text-red-600 dark:text-red-400"
                    onClick={() => setDialog({ kind: "delete", ws })}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                    <span className="hidden lg:inline">{t("admin.delete")}</span>
                  </Button>
                </div>
              </div>
              {(ws.max_documents !== null || ws.max_storage_bytes !== null) && (
                <p className="mt-1 text-xs text-zinc-400">
                  {t("admin.limits")}: {ws.max_documents !== null ? ws.max_documents : "—"} ·{" "}
                  {ws.max_storage_bytes !== null ? formatStorage(ws.max_storage_bytes ?? 0) : "—"}
                </p>
              )}
              {ws.created_at && (
                <p className="mt-0.5 text-xs text-zinc-400">
                  {formatDate(ws.created_at, language)}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}

      {dialog?.kind === "create" && (
        <CreateWorkspaceDialog
          users={users}
          onClose={() => setDialog(null)}
          onCreated={() => {
            setDialog(null);
            load();
          }}
        />
      )}
      {dialog?.kind === "rename" && dialog.ws && (
        <RenameWorkspaceDialog
          workspace={dialog.ws}
          onClose={() => setDialog(null)}
          onRenamed={() => {
            setDialog(null);
            load();
          }}
        />
      )}
      {dialog?.kind === "quota" && dialog.ws && (
        <QuotaDialog
          workspace={dialog.ws}
          onClose={() => setDialog(null)}
          onSaved={() => {
            setDialog(null);
            load();
          }}
        />
      )}
      {dialog?.kind === "members" && dialog.ws && (
        <MembersDialog
          workspace={dialog.ws}
          users={users}
          allWorkspaces={workspaces ?? []}
          onClose={() => setDialog(null)}
          onChanged={() => load()}
        />
      )}
      {dialog?.kind === "delete" && dialog.ws && (
        <Dialog open onOpenChange={(open) => !open && setDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{t("admin.deleteWorkspaceTitle")}</DialogTitle>
              <DialogDescription>
                <span className="font-medium">{dialog.ws?.name}</span> {t("admin.deleteWorkspaceConfirm")}
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialog(null)}>
                {t("common.cancel")}
              </Button>
              <Button
                variant="destructive"
                disabled={busy === dialog.ws?.id}
                onClick={() => dialog.ws && deleteWorkspace(dialog.ws)}
              >
                {t("admin.delete")}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}

function CreateWorkspaceDialog({
  users,
  onClose,
  onCreated,
}: {
  users: AdminUserOut[];
  onClose: () => void;
  onCreated: () => void;
}) {
  const { t } = useLanguage();
  const [name, setName] = useState("");
  const [ownerId, setOwnerId] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function create() {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await admin.workspaces.create({ name: name.trim(), owner_id: ownerId || null });
      onCreated();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.createFailed"));
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("admin.createTitle")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="ws-name">{t("admin.workspaceName")}</Label>
            <Input id="ws-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ws-owner">{t("admin.workspaceOwner")}</Label>
            <select id="ws-owner" value={ownerId} onChange={(e) => setOwnerId(e.target.value)} className={SELECT_CLASSES}>
              <option value="">{t("admin.emptyOwner")}</option>
              {users.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </option>
              ))}
            </select>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={create} disabled={saving || !name.trim()}>
            {saving ? t("admin.saving") : t("admin.create")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RenameWorkspaceDialog({
  workspace,
  onClose,
  onRenamed,
}: {
  workspace: AdminWorkspaceOut;
  onClose: () => void;
  onRenamed: () => void;
}) {
  const { t } = useLanguage();
  const [name, setName] = useState(workspace.name);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function rename() {
    if (!name.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await admin.workspaces.update(workspace.id, { name: name.trim() });
      onRenamed();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("admin.renameTitle")}</DialogTitle>
        </DialogHeader>
        <div className="space-y-1.5">
          <Label htmlFor="rename-name">{t("admin.workspaceName")}</Label>
          <Input id="rename-name" value={name} onChange={(e) => setName(e.target.value)} autoFocus />
        </div>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={rename} disabled={saving || !name.trim()}>
            {saving ? t("admin.saving") : t("admin.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function QuotaDialog({
  workspace,
  onClose,
  onSaved,
}: {
  workspace: AdminWorkspaceOut;
  onClose: () => void;
  onSaved: () => void;
}) {
  const { t } = useLanguage();
  const [maxDocuments, setMaxDocuments] = useState(workspace.max_documents?.toString() ?? "");
  const [maxStorageMb, setMaxStorageMb] = useState(
    workspace.max_storage_bytes != null ? String(Math.round(workspace.max_storage_bytes / (1024 * 1024))) : "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    const payload: { name?: string; max_documents?: number; max_storage_bytes?: number } = {};
    if (maxDocuments.trim() !== "") payload.max_documents = Number(maxDocuments);
    if (maxStorageMb.trim() !== "") payload.max_storage_bytes = Number(maxStorageMb) * 1024 * 1024;
    setSaving(true);
    setError(null);
    try {
      await admin.workspaces.update(workspace.id, payload);
      onSaved();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("admin.quotaTitle")}</DialogTitle>
          <DialogDescription>{t("admin.quotaDescription")}</DialogDescription>
        </DialogHeader>
        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-1.5">
            <Label htmlFor="quota-docs">{t("admin.maxDocuments")}</Label>
            <Input
              id="quota-docs"
              type="number"
              min={1}
              value={maxDocuments}
              onChange={(e) => setMaxDocuments(e.target.value)}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="quota-storage">{t("admin.maxStorageMb")}</Label>
            <Input
              id="quota-storage"
              type="number"
              min={0}
              value={maxStorageMb}
              onChange={(e) => setMaxStorageMb(e.target.value)}
            />
          </div>
        </div>
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={save} disabled={saving}>
            {saving ? t("admin.saving") : t("admin.save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MembersDialog({
  workspace,
  users,
  allWorkspaces,
  onClose,
  onChanged,
}: {
  workspace: AdminWorkspaceOut;
  users: AdminUserOut[];
  allWorkspaces: AdminWorkspaceOut[];
  onClose: () => void;
  onChanged: () => void;
}) {
  const { t } = useLanguage();
  const [members, setMembers] = useState<AdminMemberOut[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [addUserId, setAddUserId] = useState("");
  const [addRole, setAddRole] = useState<Role>("employee");
  const [busy, setBusy] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [moving, setMoving] = useState<AdminMemberOut | null>(null);

  function loadMembers() {
    admin.workspaces.members
      .list(workspace.id)
      .then((m) => setMembers(m))
      .catch((err) => setError(err instanceof Error ? err.message : t("admin.updateFailed")));
  }

  useEffect(() => {
    let cancelled = false;
    admin.workspaces.members
      .list(workspace.id)
      .then((m) => {
        if (!cancelled) setMembers(m);
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : t("admin.updateFailed"));
      });
    return () => {
      cancelled = true;
    };
  }, [workspace.id, t]);

  async function addMember() {
    if (!addUserId) return;
    setAdding(true);
    setError(null);
    try {
      await admin.workspaces.members.add(workspace.id, { user_id: addUserId, role: addRole });
      setAddUserId("");
      setAddRole("employee");
      loadMembers();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
    } finally {
      setAdding(false);
    }
  }

  async function changeRole(member: AdminMemberOut, role: Role) {
    setBusy(member.user_id);
    setError(null);
    try {
      await admin.workspaces.members.update(workspace.id, member.user_id, role);
      loadMembers();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
    } finally {
      setBusy(null);
    }
  }

  async function removeMember(member: AdminMemberOut) {
    setBusy(member.user_id);
    setError(null);
    try {
      await admin.workspaces.members.remove(workspace.id, member.user_id);
      loadMembers();
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.updateFailed"));
    } finally {
      setBusy(null);
    }
  }

  const memberIds = new Set((members ?? []).map((m) => m.user_id));
  const available = users.filter((u) => !memberIds.has(u.id));

  return (
    <>
      <Dialog open onOpenChange={(open) => !open && onClose()}>
        <DialogContent className="sm:max-w-xl">
          <DialogHeader>
            <DialogTitle>{t("admin.manageMembersTitle")}</DialogTitle>
          </DialogHeader>

        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}

        <div className="space-y-1.5">
          <Label>{t("admin.addMember")}</Label>
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={addUserId}
              onChange={(e) => setAddUserId(e.target.value)}
              className={SELECT_CLASSES}
            >
              <option value="">{t("admin.selectUser")}</option>
              {available.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.full_name || u.email}
                </option>
              ))}
            </select>
            <select
              value={addRole}
              onChange={(e) => setAddRole(e.target.value as Role)}
              className={`${SELECT_CLASSES} w-32 shrink-0`}
            >
              {ROLES.map((role) => (
                <option key={role} value={role}>
                  {t(ROLE_LABEL_KEY[role])}
                </option>
              ))}
            </select>
            <Button onClick={addMember} disabled={adding || !addUserId} className="shrink-0">
              {adding ? t("admin.saving") : t("admin.addMember")}
            </Button>
          </div>
          {available.length === 0 && <p className="text-xs text-zinc-400">{t("admin.noUsersForAdd")}</p>}
        </div>

        {members === null ? (
          <Skeleton className="h-24 w-full rounded-lg" />
        ) : members.length === 0 ? (
          <p className="text-sm text-zinc-400">{t("admin.noUsersForAdd")}</p>
        ) : (
          <ul className="space-y-1.5">
            {members.map((member) => (
              <li
                key={member.user_id}
                className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 rounded-md border px-3 py-2"
              >
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium">{member.full_name || "—"}</p>
                  <p className="truncate text-xs text-zinc-500">{member.email}</p>
                </div>
                <div className="flex shrink-0 flex-wrap items-center gap-2">
                  <RoleBadge role={member.role} />
                  {member.role !== "owner" ? (
                    <select
                      value={member.role}
                      onChange={(e) => changeRole(member, e.target.value as Role)}
                      disabled={busy === member.user_id}
                      className={`${SELECT_CLASSES} w-28`}
                    >
                      {ROLES.map((role) => (
                        <option key={role} value={role}>
                          {t(ROLE_LABEL_KEY[role])}
                        </option>
                      ))}
                    </select>
                  ) : (
                    <span className="text-xs text-zinc-400">{t("admin.ownerCannotChange")}</span>
                  )}
                  <Button
                    variant="ghost"
                    size="sm"
                    disabled={member.role === "owner" || allWorkspaces.length <= 1}
                    onClick={() => setMoving(member)}
                    className="text-zinc-500"
                  >
                    {t("admin.move")}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-red-600 hover:bg-red-500/10 hover:text-red-600 dark:text-red-400"
                    disabled={member.role === "owner" || busy === member.user_id}
                    onClick={() => removeMember(member)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </li>
            ))}
          </ul>
        )}

          <DialogFooter>
            <Button variant="outline" onClick={onClose}>
              {t("common.cancel")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {moving && (
        <MoveMemberDialog
          member={moving}
          fromWorkspaceId={workspace.id}
          targetWorkspaces={allWorkspaces.filter((w) => w.id !== workspace.id)}
          onClose={() => setMoving(null)}
          onMoved={() => {
            setMoving(null);
            loadMembers();
            onChanged();
          }}
        />
      )}
    </>
  );
}

function MoveMemberDialog({
  member,
  fromWorkspaceId,
  targetWorkspaces,
  onClose,
  onMoved,
}: {
  member: AdminMemberOut;
  fromWorkspaceId: string;
  targetWorkspaces: AdminWorkspaceOut[];
  onClose: () => void;
  onMoved: () => void;
}) {
  const { t } = useLanguage();
  const [targetId, setTargetId] = useState("");
  const [role, setRole] = useState<Role>("employee");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function move() {
    if (!targetId) return;
    setSaving(true);
    setError(null);
    try {
      await admin.moveUser(member.user_id, {
        from_workspace_id: fromWorkspaceId,
        to_workspace_id: targetId,
        role,
      });
      onMoved();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("admin.moveFailed"));
      setSaving(false);
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && !saving && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{t("admin.moveMemberTitle")}</DialogTitle>
          <DialogDescription>
            {member.full_name || member.email} — {t("admin.moveConfirm")}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="move-target">{t("admin.moveTargetWorkspace")}</Label>
            <select
              id="move-target"
              value={targetId}
              onChange={(e) => setTargetId(e.target.value)}
              className={SELECT_CLASSES}
            >
              <option value="">{t("admin.selectUser")}</option>
              {targetWorkspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  {w.name}
                </option>
              ))}
            </select>
            {targetWorkspaces.length === 0 && (
              <p className="text-xs text-zinc-400">{t("admin.noOtherWorkspaces")}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="move-role">{t("admin.memberRole")}</Label>
            <select
              id="move-role"
              value={role}
              onChange={(e) => setRole(e.target.value as Role)}
              className={SELECT_CLASSES}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {t(ROLE_LABEL_KEY[r])}
                </option>
              ))}
            </select>
          </div>
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={saving}>
            {t("common.cancel")}
          </Button>
          <Button onClick={move} disabled={saving || !targetId}>
            {saving ? t("admin.saving") : t("admin.moveConfirm")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}