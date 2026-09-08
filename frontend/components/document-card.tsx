"use client";

import { memo, useEffect, useState } from "react";
import { Check, FileText, Folder, Tag, Trash2 } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { TagBadge } from "@/components/tag-badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Skeleton } from "@/components/ui/skeleton";
import { useLanguage } from "@/lib/i18n";
import { documents } from "@/lib/api";
import type { DocumentOut, FolderOut } from "@/lib/api";

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function formatDate(value: string, locale: string): string {
  return new Date(value).toLocaleDateString(locale, { year: "numeric", month: "short", day: "numeric" });
}

const MIME_STYLES: Record<string, { label: string; icon: string }> = {
  "application/pdf": { label: "PDF", icon: "text-sky-600/90 dark:text-sky-400/90" },
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
    label: "DOCX",
    icon: "text-indigo-600/90 dark:text-indigo-400/90",
  },
};

const previewCache = new Map<string, string>();

function usePagePreview(doc: DocumentOut): string | undefined {
  const [snippet, setSnippet] = useState<string | undefined>(() =>
    previewCache.has(doc.id) ? previewCache.get(doc.id) : undefined,
  );

  useEffect(() => {
    if (doc.status !== "ready" || previewCache.has(doc.id)) return;
    let cancelled = false;
    documents
      .pages(doc.id)
      .then((pages) => {
        if (cancelled) return;
        const content = pages[0]?.content ?? "";
        previewCache.set(doc.id, content);
        setSnippet(content);
      })
      .catch(() => {
        if (cancelled) return;
        previewCache.set(doc.id, "");
        setSnippet("");
      });
    return () => {
      cancelled = true;
    };
  }, [doc.id, doc.status]);

  return snippet;
}

const DocumentPreview = memo(function DocumentPreview({ doc }: { doc: DocumentOut }) {
  const { t } = useLanguage();
  const snippet = usePagePreview(doc);
  const style = MIME_STYLES[doc.mime_type] ?? { label: "FILE", icon: "text-zinc-500/80 dark:text-zinc-400/80" };

  if (doc.status === "pending" || doc.status === "processing") {
    return <Skeleton className="absolute inset-0 h-full w-full" />;
  }

  if (doc.status === "failed") {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-2 p-4 text-center">
        <FileText className="h-7 w-7 text-red-600/80 dark:text-red-400/80" />
        <span className="line-clamp-2 text-xs text-red-600/80 dark:text-red-400/80">{t("viewer.processingFailed")}</span>
      </div>
    );
  }

  if (snippet) {
    return (
      <>
        <p className="line-clamp-6 px-4 pt-4 font-serif text-[13px] leading-6 whitespace-pre-wrap text-foreground/80">
          {snippet}
        </p>
        <div className="pointer-events-none absolute inset-x-0 bottom-0 h-1/2 bg-gradient-to-t from-muted/40 to-transparent" />
      </>
    );
  }

  if (snippet === undefined) {
    return <Skeleton className="absolute inset-0 h-full w-full" />;
  }

  return (
    <div className="flex size-full flex-col items-center justify-center gap-1.5">
      <FileText className={`h-8 w-8 ${style.icon}`} strokeWidth={1.6} />
      <span className={`text-[10px] font-medium tracking-[0.2em] ${style.icon}`}>{style.label}</span>
    </div>
  );
});

type DocumentCardProps = {
  doc: DocumentOut;
  folders: FolderOut[];
  readOnly?: boolean;
  workspaceName?: string;
  onOpen: () => void;
  onMove: (folderIds: string[]) => void;
  onEditTags: () => void;
  onDelete: () => void;
};

export const DocumentCard = memo(function DocumentCard({
  doc,
  folders,
  readOnly = false,
  workspaceName,
  onOpen,
  onMove,
  onEditTags,
  onDelete,
}: DocumentCardProps) {
  const { language, t } = useLanguage();

  return (
    <article className="group flex flex-col overflow-hidden rounded-display border bg-card shadow-xs transition-all hover:-translate-y-px hover:shadow-md">
      <button type="button" onClick={onOpen} className="relative block w-full cursor-pointer text-left">
        <div className="relative aspect-[4/3] w-full overflow-hidden bg-muted/40">
          <DocumentPreview doc={doc} />
        </div>
      </button>

      <div className="flex flex-1 flex-col gap-2 border-t p-3">
        <div className="flex items-start justify-between gap-2">
          <button type="button" onClick={onOpen} className="min-w-0 cursor-pointer text-left">
            <p className="truncate text-sm font-medium group-hover:underline">{doc.filename}</p>
          </button>
          <StatusBadge status={doc.status} />
        </div>
        <p className="truncate text-xs text-zinc-500">
          {formatDate(doc.created_at, language)} · {formatBytes(doc.size_bytes)}
          {doc.page_count != null
            ? ` · ${doc.page_count} ${doc.page_count === 1 ? t("documents.page") : t("documents.pages")}`
            : ""}
          {doc.folders.length > 0 ? ` · ${doc.folders.map((f) => f.name).join(", ")}` : ""}
          {workspaceName ? ` · ${workspaceName}` : ""}
        </p>
        {doc.tags.length > 0 && (
          <span className="flex flex-wrap gap-1">
            {doc.tags.map((tag) => (
              <TagBadge key={tag.id} tag={tag} />
            ))}
          </span>
        )}
        {!readOnly && (
          <div className="mt-auto flex items-center gap-1 border-t pt-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm" aria-label={`${t("documents.move")} ${doc.filename}`}>
                <Folder className="h-4 w-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-52">
              <DropdownMenuLabel>{t("folders.moveToFolder")}</DropdownMenuLabel>
              <DropdownMenuItem onSelect={() => onMove([])}>
                <Check className={doc.folders.length === 0 ? "opacity-100" : "opacity-0"} />
                {t("folders.noFolder")}
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              {folders.length === 0 && <DropdownMenuItem disabled>{t("folders.createFirst")}</DropdownMenuItem>}
              {folders.map((f) => {
                const isIn = doc.folders.some((df) => df.id === f.id);
                return (
                  <DropdownMenuItem key={f.id} onSelect={() => onMove(isIn ? [] : [f.id])}>
                    <Check className={isIn ? "opacity-100" : "opacity-0"} />
                    {f.name}
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
          <Button variant="ghost" size="sm" aria-label={`${t("tags.edit")} ${doc.filename}`} onClick={onEditTags}>
            <Tag className="h-4 w-4" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            aria-label={`${t("documents.delete")} ${doc.filename}`}
            onClick={onDelete}
            className="ml-auto"
          >
            <Trash2 className="h-4 w-4" />
          </Button>
          </div>
        )}
      </div>
    </article>
  );
});