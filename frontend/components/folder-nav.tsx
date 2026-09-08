"use client";

import { useState } from "react";
import { Folder, FolderInput, FolderOpen, FolderPlus, MoreHorizontal, Pencil, Trash2 } from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { useLanguage } from "@/lib/i18n";
import { folders as foldersApi } from "@/lib/api";
import type { FolderOut } from "@/lib/api";

export type FolderFilter = { kind: "all" } | { kind: "unfiled" } | { kind: "folder"; folderId: string };

export function FolderNav({
  workspaceId,
  folders,
  active,
  onSelect,
  onChanged,
}: {
  workspaceId: string | null;
  folders: FolderOut[];
  active: FolderFilter;
  onSelect: (filter: FolderFilter) => void;
  onChanged: () => void;
}) {
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const { t } = useLanguage();

  function isActive(filter: FolderFilter): boolean {
    if (active.kind !== filter.kind) return false;
    if (filter.kind === "folder" && active.kind === "folder") return active.folderId === filter.folderId;
    return true;
  }

  async function createFolder() {
    if (!workspaceId || !newName.trim()) return;
    setError(null);
    try {
      await foldersApi.create(workspaceId, newName.trim());
      setNewName("");
      setCreating(false);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("folders.createFailed"));
    }
  }

  async function renameFolder(folderId: string) {
    if (!editName.trim()) return;
    setError(null);
    try {
      await foldersApi.rename(folderId, editName.trim());
      setEditingId(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("folders.renameFailed"));
    }
  }

  async function deleteFolder(folderId: string) {
    setError(null);
    try {
      await foldersApi.remove(folderId);
      if (active.kind === "folder" && active.folderId === folderId) onSelect({ kind: "all" });
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("folders.deleteFailed"));
    }
  }

  return (
    <nav className="space-y-1">
      <button
        type="button"
        onClick={() => onSelect({ kind: "all" })}
        className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
          isActive({ kind: "all" })
            ? "bg-zinc-900 font-medium text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900"
            : "text-zinc-700 hover:bg-muted dark:text-zinc-300"
        }`}
      >
        <FolderOpen className="h-4 w-4 shrink-0" />
        {t("folders.allDocuments")}
        <span className="ml-auto text-xs opacity-60">{folders.reduce((sum, f) => sum + f.document_count, 0)}</span>
      </button>

      {folders.map((folder) =>
        editingId === folder.id ? (
          <div key={folder.id} className="px-1 py-0.5">
            <Input
              autoFocus
              value={editName}
              maxLength={255}
              className="h-8 text-sm"
              onChange={(e) => setEditName(e.target.value)}
              onBlur={() => setEditingId(null)}
              onKeyDown={(e) => {
                if (e.key === "Enter") renameFolder(folder.id);
                if (e.key === "Escape") setEditingId(null);
              }}
            />
          </div>
        ) : (
          <div
            key={folder.id}
            className={`group flex items-center rounded-lg transition-colors ${
              isActive({ kind: "folder", folderId: folder.id }) ? "bg-muted" : "hover:bg-muted/60"
            }`}
          >
            <button
              type="button"
              onClick={() => onSelect({ kind: "folder", folderId: folder.id })}
              className={`flex min-w-0 flex-1 items-center gap-2 px-3 py-2 text-left text-sm ${
                isActive({ kind: "folder", folderId: folder.id })
                  ? "font-medium text-zinc-900 dark:text-zinc-100"
                  : "text-zinc-700 dark:text-zinc-300"
              }`}
            >
              <Folder className="h-4 w-4 shrink-0 text-zinc-400" />
              <span className="truncate">{folder.name}</span>
              <span className="ml-auto text-xs text-zinc-400">{folder.document_count}</span>
            </button>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  aria-label={`${t("folders.optionsFor")} ${folder.name}`}
                  className="mr-1 size-7 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100"
                >
                  <MoreHorizontal className="h-3.5 w-3.5" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="w-40">
                <DropdownMenuItem
                  onSelect={() => {
                    setEditingId(folder.id);
                    setEditName(folder.name);
                  }}
                >
                  <Pencil />
                  {t("folders.rename")}
                </DropdownMenuItem>
                <DropdownMenuItem variant="destructive" className="bg-destructive/10" onSelect={() => deleteFolder(folder.id)}>
                  <Trash2 />
                  {t("folders.delete")}
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        ),
      )}

      <button
        type="button"
        onClick={() => onSelect({ kind: "unfiled" })}
        className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm transition-colors ${
          isActive({ kind: "unfiled" })
            ? "bg-zinc-900 font-medium text-zinc-50 dark:bg-zinc-100 dark:text-zinc-900"
            : "text-zinc-700 hover:bg-muted dark:text-zinc-300"
        }`}
      >
        <FolderInput className="h-4 w-4 shrink-0" />
        {t("folders.unfiled")}
      </button>

      {creating ? (
        <div className="px-1 py-0.5">
          <Input
            autoFocus
            value={newName}
            maxLength={255}
            placeholder={t("folders.folderNamePlaceholder")}
            className="h-8 text-sm"
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                createFolder();
                setCreating(false);
              }
              if (e.key === "Escape") setCreating(false);
            }}
          />
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setCreating(true)}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-sm text-zinc-500 transition-colors hover:bg-muted hover:text-zinc-800 dark:hover:text-zinc-200"
        >
          <FolderPlus className="h-4 w-4 shrink-0" />
          {t("folders.newFolder")}
        </button>
      )}

      {error && <p className="px-3 pt-1 text-xs text-red-600 dark:text-red-400">{error}</p>}
    </nav>
  );
}
