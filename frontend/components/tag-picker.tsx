"use client";

import { useEffect, useState } from "react";
import { Plus } from "lucide-react";

import { TagBadge } from "@/components/tag-badge";
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
import { useLanguage } from "@/lib/i18n";
import { tags as tagsApi, documents as documentsApi } from "@/lib/api";
import type { TagOut } from "@/lib/api";

export const TAG_COLORS = [
  "#6b7280",
  "#ef4444",
  "#f97316",
  "#eab308",
  "#22c55e",
  "#3b82f6",
  "#8b5cf6",
  "#ec4899",
];

export function TagPicker({
  open,
  onOpenChange,
  workspaceId,
  documentId,
  documentTagIds,
  onChanged,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  workspaceId: string | null;
  documentId: string;
  documentTagIds: string[];
  onChanged: (updated: TagOut[]) => void;
}) {
  const [available, setAvailable] = useState<TagOut[]>([]);
  const [selected, setSelected] = useState<Set<string>>(() => new Set(documentTagIds));
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [color, setColor] = useState(TAG_COLORS[5]);
  const [scope, setScope] = useState<"user" | "global">("global");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const { t } = useLanguage();

  function handleOpenChange(next: boolean) {
    if (next) setSelected(new Set(documentTagIds));
    onOpenChange(next);
  }

  useEffect(() => {
    if (!open || !workspaceId) return;
    tagsApi
      .list(workspaceId)
      .then(setAvailable)
      .catch((err) => setError(err instanceof Error ? err.message : t("tags.failedToLoad")));
  }, [open, workspaceId, t]);

  function toggle(tagId: string) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(tagId)) next.delete(tagId);
      else next.add(tagId);
      return next;
    });
  }

  async function save() {
    setSaving(true);
    setError(null);
    try {
      const updated = await documentsApi.setTags(documentId, [...selected]);
      onChanged(updated.tags);
      onOpenChange(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("tags.updateFailed"));
    } finally {
      setSaving(false);
    }
  }

  async function createTag() {
    if (!workspaceId || !name.trim()) return;
    setError(null);
    try {
      const created = await tagsApi.create(workspaceId, { name: name.trim(), color, scope });
      setAvailable((prev) => [...prev, created].sort((a, b) => a.name.localeCompare(b.name)));
      setSelected((prev) => new Set(prev).add(created.id));
      setName("");
      setCreating(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : t("tags.createFailed"));
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t("tags.manage")}</DialogTitle>
          <DialogDescription>{t("tags.selectForDocument")}</DialogDescription>
        </DialogHeader>

        {!creating ? (
          <Button variant="outline" size="sm" className="w-fit" onClick={() => setCreating(true)}>
            <Plus className="mr-1.5 h-4 w-4" />
            {t("tags.new")}
          </Button>
        ) : (
          <div className="space-y-3 rounded-lg border p-3">
            <div className="space-y-2">
              <Label htmlFor="tag-name">{t("tags.name")}</Label>
              <Input
                id="tag-name"
                value={name}
                maxLength={100}
                placeholder={t("tags.namePlaceholder")}
                onChange={(e) => setName(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && createTag()}
              />
            </div>
            <div className="space-y-2">
              <Label>{t("tags.color")}</Label>
              <div className="flex flex-wrap gap-2">
                {TAG_COLORS.map((c) => (
                  <button
                    key={c}
                    type="button"
                    aria-label={`${t("tags.useColor")} ${c}`}
                    onClick={() => setColor(c)}
                    className={`size-6 rounded-full transition-transform ${
                      color === c ? "scale-110 ring-2 ring-ring ring-offset-2 ring-offset-background" : ""
                    }`}
                    style={{ backgroundColor: c }}
                  />
                ))}
              </div>
            </div>
            <div className="space-y-2">
              <Label>{t("tags.visibility")}</Label>
              <div className="flex gap-2">
                <Button
                  type="button"
                  size="sm"
                  variant={scope === "global" ? "default" : "outline"}
                  onClick={() => setScope("global")}
                >
                  {t("tags.workspace")}
                </Button>
                <Button
                  type="button"
                  size="sm"
                  variant={scope === "user" ? "default" : "outline"}
                  onClick={() => setScope("user")}
                >
                  {t("tags.onlyMe")}
                </Button>
              </div>
            </div>
            <div className="flex gap-2">
              <Button size="sm" onClick={createTag} disabled={!name.trim()}>
                {t("tags.create")}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setCreating(false)}>
                {t("common.cancel")}
              </Button>
            </div>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {available.length === 0 && !creating && (
            <p className="text-sm text-zinc-500">{t("tags.noneYetHint")}</p>
          )}
          {available.map((tag) => (
            <button key={tag.id} type="button" onClick={() => toggle(tag.id)} className="transition-opacity">
              <span className={selected.has(tag.id) ? "" : "opacity-40"}>
                <TagBadge tag={tag} />
              </span>
            </button>
          ))}
        </div>

        {error && <p className="text-sm text-red-600 dark:text-red-400">{error}</p>}

        <DialogFooter>
          <Button onClick={save} disabled={saving}>
            {saving ? t("common.saving") : t("common.done")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
