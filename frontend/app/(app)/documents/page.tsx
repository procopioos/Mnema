"use client";

import { useCallback, useEffect, useMemo, useRef, useState, useSyncExternalStore } from "react";
import { useRouter } from "next/navigation";
import { Check, Folder, Tag, Trash2, Upload } from "lucide-react";

import { FolderNav, type FolderFilter } from "@/components/folder-nav";
import { StatusBadge } from "@/components/status-badge";
import { TagBadge } from "@/components/tag-badge";
import { TagPicker } from "@/components/tag-picker";
import { EmptyIllustration } from "@/components/empty-illustration";
import { Blob } from "@/components/doodles";
import { DocumentCard, formatBytes, formatDate } from "@/components/document-card";
import { ViewToggle, type ViewMode } from "@/components/view-toggle";
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
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { canManage } from "@/lib/roles";
import { documents, folders as foldersApi, tags as tagsApi, workspaces as workspacesApi } from "@/lib/api";
import type { DocumentOut, FolderOut, PublicDocumentOut, TagOut, WorkspaceOut } from "@/lib/api";
import type { TranslationKey } from "@/lib/i18n";
import { VisibilityBadge } from "@/components/visibility-badge";
import { RoleBadge } from "@/components/role-badge";

const VIEW_KEY = "mnema.documents.view";

const QUOTA_ERROR_KEY: Record<string, TranslationKey> = {
  documents_count_exceeded: "documents.quotaDocumentsExceeded",
  storage_exceeded: "documents.quotaStorageExceeded",
};

const viewModeListeners = new Set<() => void>();
function subscribeViewMode(listener: () => void) {
  viewModeListeners.add(listener);
  return () => { viewModeListeners.delete(listener); };
}
function getViewModeSnapshot(): ViewMode {
  try { return localStorage.getItem(VIEW_KEY) === "grid" ? "grid" : "list"; } catch { return "list"; }
}
function getViewModeServerSnapshot(): ViewMode { return "list"; }

export default function DocumentsPage() {
  const { workspaceId, role } = useAuth();
  const { language, t } = useLanguage();
  const tRef = useRef(t);
  useEffect(() => { tRef.current = t; }, [t]);
  const router = useRouter();
  const [docs, setDocs] = useState<DocumentOut[] | null>(null);
  const [folders, setFolders] = useState<FolderOut[]>([]);
  const [allTags, setAllTags] = useState<TagOut[]>([]);
  const [filter, setFilter] = useState<FolderFilter>({ kind: "all" });
  const [selectedTagId, setSelectedTagId] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [toDelete, setToDelete] = useState<DocumentOut | null>(null);
  const [pickerDoc, setPickerDoc] = useState<DocumentOut | null>(null);
  const [scope, setScope] = useState<"workspace" | "public">("workspace");
  const [publicDocs, setPublicDocs] = useState<PublicDocumentOut[] | null>(null);
  const [makePublic, setMakePublic] = useState(false);
  const [workspace, setWorkspace] = useState<WorkspaceOut | null>(null);
  const viewMode = useSyncExternalStore(subscribeViewMode, getViewModeSnapshot, getViewModeServerSnapshot);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const setViewMode = useCallback((mode: ViewMode) => {
    try { localStorage.setItem(VIEW_KEY, mode); } catch { /* storage unavailable */ }
    viewModeListeners.forEach((l) => l());
  }, []);

  const listParams = useMemo(
    () => ({
      folderId: filter.kind === "folder" ? filter.folderId : undefined,
      unfiled: filter.kind === "unfiled",
      tagId: selectedTagId ?? undefined,
    }),
    [filter, selectedTagId],
  );

  const loadDocs = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const res = await documents.list(workspaceId, { ...listParams, limit: 200 });
      setDocs(res.items);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : tRef.current("documents.failedToLoad"));
    }
  }, [workspaceId, listParams]);

  const loadSidebar = useCallback(async () => {
    if (!workspaceId) return;
    try {
      const [folderList, tagList] = await Promise.all([foldersApi.list(workspaceId), tagsApi.list(workspaceId)]);
      setFolders(folderList);
      setAllTags(tagList);
    } catch (err) {
      setError(err instanceof Error ? err.message : tRef.current("folders.failedToLoad"));
    }
  }, [workspaceId]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const [res, folderList, tagList, ws] = await Promise.all([
          documents.list(workspaceId ?? "", { ...listParams, limit: 200 }),
          workspaceId ? foldersApi.list(workspaceId) : [],
          workspaceId ? tagsApi.list(workspaceId) : [],
          workspaceId ? workspacesApi.get(workspaceId) : null,
        ]);
        if (cancelled || !workspaceId) return;
        setDocs(res.items);
        setFolders(folderList);
        setAllTags(tagList);
        setWorkspace(ws);
        setError(null);
      } catch (err) {
        if (cancelled || !workspaceId) return;
        setError(err instanceof Error ? err.message : tRef.current("documents.failedToLoad"));
      }
    })();
    return () => { cancelled = true; };
  }, [workspaceId, listParams]);

  const refresh = useCallback(async () => {
    if (!workspaceId) return;
    await Promise.all([loadDocs(), loadSidebar(), workspacesApi.get(workspaceId).then(setWorkspace)]);
  }, [loadDocs, loadSidebar, workspaceId]);

  useEffect(() => {
    if (scope !== "public") return;
    let cancelled = false;
    documents
      .listPublic({ limit: 200 })
      .then((res) => {
        if (cancelled) return;
        setPublicDocs(res.items);
        setError(null);
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err instanceof Error ? err.message : tRef.current("documents.failedToLoad"));
      });
    return () => {
      cancelled = true;
    };
  }, [scope]);

  useEffect(() => {
    if (scope !== "workspace") return;
    const hasActive = (docs ?? []).some((d) => d.status === "pending" || d.status === "processing");
    if (!hasActive) return;
    let timer: ReturnType<typeof setTimeout>;
    let cancelled = false;
    let backoffIdx = 0;
    const BASE = [2000, 5000, 15000];

    const schedule = (delay: number) => {
      timer = setTimeout(poll, document.hidden ? 10000 : delay);
    };

    const poll = async () => {
      if (cancelled) return;
      await loadDocs();
      if (cancelled) return;
      const delay = BASE[Math.min(backoffIdx, BASE.length - 1)];
      backoffIdx += 1;
      schedule(delay);
    };

    schedule(BASE[0]);

    const onVisibility = () => {
      clearTimeout(timer);
      backoffIdx = 0;
      schedule(BASE[0]);
    };
    document.addEventListener("visibilitychange", onVisibility);
    return () => {
      cancelled = true;
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisibility);
    };
  }, [docs, loadDocs, scope]);

  async function handleFile(file: File) {
    if (!workspaceId) return;
    setUploading(true);
    setError(null);
    try {
      await documents.upload(workspaceId, file, makePublic);
      await refresh();
    } catch (err) {
      const key = err instanceof Error ? QUOTA_ERROR_KEY[err.message] : undefined;
      setError(key ? t(key) : err instanceof Error ? err.message : t("documents.uploadFailed"));
    } finally {
      setUploading(false);
      setMakePublic(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  async function confirmDelete() {
    if (!toDelete) return;
    try {
      await documents.remove(toDelete.id);
      setToDelete(null);
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("documents.deleteFailed"));
      setToDelete(null);
    }
  }

  async function moveToFolder(doc: DocumentOut, folderIds: string[]) {
    try {
      const updated = await documents.setFolders(doc.id, folderIds);
      setDocs((prev) => (prev ? prev.map((d) => (d.id === updated.id ? updated : d)) : prev));
      if (workspaceId) setFolders(await foldersApi.list(workspaceId));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("documents.moveFailed"));
    }
  }

  function heading(): string {
    if (filter.kind === "unfiled") return t("folders.unfiled");
    if (filter.kind === "folder") {
      return folders.find((f) => f.id === filter.folderId)?.name ?? t("folders.folder");
    }
    return t("nav.documents");
  }

  function folderNamesFor(doc: DocumentOut): string {
    if (doc.folders.length === 0) return "";
    return doc.folders.map((f) => f.name).join(", ");
  }

  const visibleDocs = (scope === "public" ? publicDocs : docs) as (DocumentOut | PublicDocumentOut)[] | null;
  const editable = scope === "workspace" && canManage(role);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-3xl font-semibold tracking-tight">{heading()}</h1>
          {scope === "workspace" && role && (
            <div className="mt-1.5">
              <RoleBadge role={role} />
            </div>
          )}
          <p className="mt-1 text-sm text-zinc-500">
            {scope === "public" ? t("documents.publicScopeDescription") : t("documents.description")}
          </p>
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.txt,.md"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
          }}
        />
        <div className="flex items-center gap-2">
          <div
            role="tablist"
            aria-label={t("documents.visibility")}
            className="flex items-center gap-0.5 rounded-lg border bg-card p-0.5 shadow-xs"
          >
            <button
              type="button"
              role="tab"
              aria-selected={scope === "workspace"}
              onClick={() => setScope("workspace")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                scope === "workspace"
                  ? "bg-muted text-foreground"
                  : "text-zinc-400 hover:text-foreground"
              }`}
            >
              {t("documents.workspaceScope")}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={scope === "public"}
              onClick={() => setScope("public")}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                scope === "public"
                  ? "bg-muted text-foreground"
                  : "text-zinc-400 hover:text-foreground"
              }`}
            >
              {t("documents.publicScope")}
            </button>
          </div>
          <ViewToggle value={viewMode} onChange={setViewMode} />
          {scope === "workspace" && (
            <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
              <Upload className="mr-2 h-4 w-4" />
              {uploading ? t("documents.uploading") : t("documents.upload")}
            </Button>
          )}
        </div>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <div className={scope === "workspace" ? "grid gap-6 md:grid-cols-[240px_1fr]" : "space-y-4"}>
        {scope === "workspace" && (
          <aside className="space-y-5 self-start rounded-display border bg-card p-3 shadow-xs">
            <FolderNav
              workspaceId={workspaceId}
              folders={folders}
              active={filter}
              onSelect={setFilter}
              onChanged={loadSidebar}
            />

          <div className="border-t pt-3">
            <p className="mb-2 px-3 text-xs font-medium tracking-wide text-zinc-400 uppercase">{t("tags.title")}</p>
            <div className="flex flex-wrap gap-1.5 px-1.5 pb-1">
              <button
                type="button"
                onClick={() => setSelectedTagId(null)}
                className={`rounded-full border px-2 py-0.5 text-xs transition-colors ${
                  selectedTagId === null
                    ? "border-zinc-900 bg-zinc-900 text-zinc-50 dark:border-zinc-100 dark:bg-zinc-100 dark:text-zinc-900"
                    : "border-border text-zinc-600 hover:bg-muted dark:text-zinc-400"
                }`}
              >
                {t("tags.any")}
              </button>
              {allTags.map((tag) => (
                <button key={tag.id} type="button" onClick={() => setSelectedTagId(selectedTagId === tag.id ? null : tag.id)}>
                  <span className={selectedTagId === tag.id ? "" : "opacity-60 hover:opacity-100"}>
                    <TagBadge tag={tag} />
                  </span>
                </button>
              ))}
              {allTags.length === 0 && <p className="px-1 py-0.5 text-xs text-zinc-400">{t("tags.noneYet")}</p>}
            </div>
          </div>
          </aside>
        )}

        <main className="min-w-0 space-y-4">
          {scope === "workspace" && (
            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragging(true);
              }}
              onDragLeave={() => setDragging(false)}
              onDrop={(e) => {
                e.preventDefault();
                setDragging(false);
                const file = e.dataTransfer.files?.[0];
                if (file) handleFile(file);
              }}
              className={`rounded-lg border-2 border-dashed p-8 text-center transition-all ${
                dragging
                  ? "scale-[1.01] border-zinc-900 bg-zinc-100 dark:border-zinc-100 dark:bg-zinc-900"
                  : "border-zinc-300 bg-gradient-to-b from-muted/40 to-transparent hover:border-zinc-400 dark:border-zinc-700 dark:hover:border-zinc-600"
              }`}
            >
              <span className="relative mx-auto flex size-14 items-center justify-center">
                <Blob className="absolute -inset-2 h-16 w-16 text-foreground/5" />
                <span className="relative flex size-10 items-center justify-center rounded-full bg-background shadow-xs">
                  <Upload className="float h-5 w-5 text-zinc-400" />
                </span>
              </span>
              <p className="mt-3 text-sm text-zinc-500">{t("documents.dragDrop")}</p>
              <label className="mt-3 inline-flex items-start gap-2 text-left text-sm text-zinc-500">
                <input
                  type="checkbox"
                  checked={makePublic}
                  onChange={(e) => setMakePublic(e.target.checked)}
                  className="mt-0.5 accent-zinc-900 dark:accent-zinc-100"
                />
                <span>
                  <span className="font-medium">{t("documents.uploadPublic")}</span>
                  <span className="block text-xs text-zinc-400">{t("documents.uploadPublicHint")}</span>
                </span>
              </label>
              {workspace && (
                <p className="mt-3 text-center text-xs text-zinc-400">
                  {workspace.document_count} / {workspace.max_documents} {t("documents.documents")}
                  <span aria-hidden> · </span>
                  {formatBytes(workspace.storage_bytes)} / {formatBytes(workspace.max_storage_bytes)}
                </p>
              )}
            </div>
          )}

          <div className={viewMode === "list" ? "space-y-2" : "grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4"}>
            {visibleDocs === null ? (
              viewMode === "list" ? (
                <>
                  <Skeleton className="h-14 w-full rounded-lg" />
                  <Skeleton className="h-14 w-full rounded-lg" />
                  <Skeleton className="h-14 w-full rounded-lg" />
                </>
              ) : (
                <>
                  <Skeleton className="aspect-[4/3] w-full rounded-display" />
                  <Skeleton className="aspect-[4/3] w-full rounded-display" />
                  <Skeleton className="aspect-[4/3] w-full rounded-display" />
                </>
              )
            ) : visibleDocs.length === 0 ? (
              <div
                className={
                  viewMode === "list"
                    ? "flex flex-col items-center gap-2 py-12 text-center"
                    : "col-span-full flex flex-col items-center gap-2 py-12 text-center"
                }
              >
                <EmptyIllustration className="mt-2" />
                <p className="text-sm font-medium">{t("documents.noDocuments")}</p>
                <p className="text-sm text-zinc-500">
                  {scope === "public"
                    ? t("documents.publicScopeDescription")
                    : filter.kind === "all" && !selectedTagId
                      ? t("documents.firstFileHint")
                      : t("documents.tryDifferentFilter")}
                </p>
                {scope === "workspace" && (
                  <Button variant="outline" size="sm" onClick={() => fileInputRef.current?.click()} disabled={uploading}>
                    <Upload className="mr-1.5 h-4 w-4" />
                    {t("documents.uploadDocument")}
                  </Button>
                )}
              </div>
            ) : viewMode === "list" ? (
              visibleDocs.map((doc) => (
                <div
                  key={doc.id}
                  className="group tilt-row tilted flex items-center justify-between gap-4 rounded-lg border bg-card px-4 py-3 shadow-xs transition-all hover:border-ring/40 hover:shadow-md"
                >
                  <button
                    type="button"
                    onClick={() => router.push(`/documents/${doc.id}`)}
                    className="flex min-w-0 flex-1 items-center gap-3 text-left"
                  >
                    <div className="min-w-0">
                      <p className="truncate font-medium">{doc.filename}</p>
                      <p className="truncate text-xs text-zinc-500">
                        {formatDate(doc.created_at, language)} · {formatBytes(doc.size_bytes)}
                        {doc.page_count != null
                          ? ` · ${doc.page_count} ${doc.page_count === 1 ? t("documents.page") : t("documents.pages")}`
                          : ""}
                        {doc.folders.length > 0 ? ` · ${folderNamesFor(doc)}` : ""}
                        {"workspace_name" in doc ? ` · ${doc.workspace_name}` : ""}
                      </p>
                      {doc.tags.length > 0 && (
                        <span className="mt-1.5 flex flex-wrap gap-1">
                          {doc.tags.map((tag) => (
                            <TagBadge key={tag.id} tag={tag} />
                          ))}
                        </span>
                      )}
                    </div>
                  </button>
                  <div className="flex items-center gap-2">
                    <VisibilityBadge isPublic={doc.is_public} />
                    <StatusBadge status={doc.status} />
                    {doc.status === "failed" && doc.error_message && (
                      <span className="max-w-52 truncate text-xs text-red-600 dark:text-red-400" title={doc.error_message}>
                        {doc.error_message}
                      </span>
                    )}
                    {editable && (
                      <>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm" aria-label={`${t("documents.move")} ${doc.filename}`}>
                              <Folder className="h-4 w-4" />
                              <span className="hidden lg:inline">{t("documents.move")}</span>
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end" className="w-52">
                            <DropdownMenuLabel>{t("folders.moveToFolder")}</DropdownMenuLabel>
                            <DropdownMenuItem onSelect={() => moveToFolder(doc, [])}>
                              <Check className={doc.folders.length === 0 ? "opacity-100" : "opacity-0"} />
                              {t("folders.noFolder")}
                            </DropdownMenuItem>
                            <DropdownMenuSeparator />
                            {folders.length === 0 && (
                              <DropdownMenuItem disabled>{t("folders.createFirst")}</DropdownMenuItem>
                            )}
                            {folders.map((f) => {
                              const isIn = doc.folders.some((df) => df.id === f.id);
                              return (
                                <DropdownMenuItem key={f.id} onSelect={() => moveToFolder(doc, isIn ? [] : [f.id])}>
                                  <Check className={isIn ? "opacity-100" : "opacity-0"} />
                                  {f.name}
                                </DropdownMenuItem>
                              );
                            })}
                          </DropdownMenuContent>
                        </DropdownMenu>
                        <Button variant="ghost" size="sm" aria-label={`${t("tags.edit")} ${doc.filename}`} onClick={() => setPickerDoc(doc)}>
                          <Tag className="h-4 w-4" />
                          <span className="hidden lg:inline">{t("tags.title")}</span>
                        </Button>
                        <Button variant="ghost" size="icon" aria-label={`${t("documents.delete")} ${doc.filename}`} onClick={() => setToDelete(doc)}>
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              ))
            ) : (
              visibleDocs.map((doc) => (
                <DocumentCard
                  key={doc.id}
                  doc={doc}
                  folders={folders}
                  readOnly={!editable}
                  workspaceName={"workspace_name" in doc ? doc.workspace_name : undefined}
                  onOpen={() => router.push(`/documents/${doc.id}`)}
                  onMove={(folderIds) => moveToFolder(doc, folderIds)}
                  onEditTags={() => setPickerDoc(doc)}
                  onDelete={() => setToDelete(doc)}
                />
              ))
            )}
          </div>
        </main>
      </div>

      <Dialog open={toDelete !== null} onOpenChange={(open) => !open && setToDelete(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("documents.deleteTitle")}</DialogTitle>
            <DialogDescription>
              <span className="font-medium">{toDelete?.filename}</span> {t("documents.deleteDescription")}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setToDelete(null)}>
              {t("common.cancel")}
            </Button>
            <Button variant="destructive" onClick={confirmDelete}>
              {t("documents.delete")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {pickerDoc && (
        <TagPicker
          open={pickerDoc !== null}
          onOpenChange={(open) => !open && setPickerDoc(null)}
          workspaceId={workspaceId}
          documentId={pickerDoc.id}
          documentTagIds={pickerDoc.tags.map((t) => t.id)}
          onChanged={(updatedTags) => {
            setDocs((prev) =>
              prev ? prev.map((d) => (d.id === pickerDoc.id ? { ...d, tags: updatedTags } : d)) : prev,
            );
            setPickerDoc((prev) => (prev ? { ...prev, tags: updatedTags } : prev));
          }}
        />
      )}
    </div>
  );
}
