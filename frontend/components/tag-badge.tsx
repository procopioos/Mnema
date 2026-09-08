"use client";

import { memo } from "react";
import { Tag as TagIcon } from "lucide-react";

import { useLanguage } from "@/lib/i18n";
import type { TagOut } from "@/lib/api";

export const TagBadge = memo(function TagBadge({ tag, onRemove }: { tag: TagOut; onRemove?: () => void }) {
  const { t } = useLanguage();
  return (
    <span
      className="inline-flex h-5 shrink-0 items-center gap-1 rounded-4xl border border-transparent px-2 py-0.5 text-xs font-medium whitespace-nowrap"
      style={{ backgroundColor: `${tag.color}1f`, color: tag.color }}
      title={tag.user_id ? t("tags.personalTag") : t("tags.workspaceTag")}
    >
      <TagIcon className="size-3" />
      {tag.name}
      {onRemove && (
        <button
          type="button"
          aria-label={`${t("tags.removeTag")} ${tag.name}`}
          onClick={(e) => {
            e.stopPropagation();
            onRemove();
          }}
          className="-mr-1 rounded-full p-0.5 transition-colors hover:bg-black/10 dark:hover:bg-white/10"
        >
          <span aria-hidden className="text-[10px] leading-none">
            ✕
          </span>
        </button>
      )}
    </span>
  );
});