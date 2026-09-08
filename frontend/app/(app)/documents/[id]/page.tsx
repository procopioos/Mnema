"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState, useCallback } from "react";
import { Check, ChevronLeft, ChevronRight, Folder, FolderInput, Globe2, Lock, Pencil } from "lucide-react";
import dynamic from "next/dynamic";
import remarkGfm from "remark-gfm";

import { StatusBadge } from "@/components/status-badge";
import { TagBadge } from "@/components/tag-badge";
import { TagPicker } from "@/components/tag-picker";
import { VisibilityBadge } from "@/components/visibility-badge";
import { Sparkles } from "@/components/doodles";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Separator } from "@/components/ui/separator";
import { Skeleton } from "@/components/ui/skeleton";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { canManage } from "@/lib/roles";
import { documents, folders as foldersApi } from "@/lib/api";
import type { DocumentOut, DocumentPageOut, FolderOut } from "@/lib/api";

type View = "text" | "pdf" | "preview";

const ReactMarkdown = dynamic(() => import("react-markdown"), { ssr: false });

export default function DocumentViewerPage() {
  const params = useParams<{ id: string }>();
  const id = params.id;
  const { workspaceId, role } = useAuth();
  const { t } = useLanguage();
  const [doc, setDoc] = useState<DocumentOut | null>(null);
  const [folders, setFolders] = useState<FolderOut[]>([]);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pages, setPages] = useState<DocumentPageOut[] | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [fileBlob, setFileBlob] = useState<Blob | null>(null);
  const [previewText, setPreviewText] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [error, setError] = useState<string | null>(null);
  const [view, setView] = useState<View>("text");
  const previewRef = useRef<HTMLDivElement>(null);

  const objectUrlRef = useRef<string | null>(null);

  const toggleVisibility = useCallback(async () => {
    if (!doc) return;
    try {
      setDoc(await documents.setVisibility(doc.id, !doc.is_public));
    } catch (err) {
      setError(err instanceof Error ? err.message : t("documents.visibilityFailed"));
    }
  }, [doc, t]);

  useEffect(() => {
    const controller = new AbortController();
    documents
      .get(id)
      .then((d) => {
        setDoc(d);
        if (d.status === "ready") {
          return documents.pages(id).then((p) => {
            setPages(p);
            if (p.length > 0) setCurrentPage(1);
          });
        }
      })
      .catch((err) => {
        if (!controller.signal.aborted) setError(err instanceof Error ? err.message : t("viewer.failedToLoad"));
      });
    return () => controller.abort();
  }, [id, t]);

  useEffect(() => {
    if (!workspaceId) return;
    const controller = new AbortController();
    foldersApi
      .list(workspaceId)
      .then(setFolders)
      .catch(() => setFolders([]));
    return () => controller.abort();
  }, [workspaceId]);

  useEffect(() => {
    if (view !== "pdf" && view !== "preview") return;
    if (fileBlob) return;
    if (!doc || doc.status !== "ready") return;
    let cancelled = false;
    const controller = new AbortController();
    documents
      .file(id)
      .then((blob) => {
        if (cancelled || controller.signal.aborted) return;
        const objectUrl = URL.createObjectURL(blob);
        objectUrlRef.current = objectUrl;
        setPdfUrl(objectUrl);
        setFileBlob(blob);
      })
      .catch((err) => {
        if (!controller.signal.aborted && !cancelled) {
          setError(err instanceof Error ? err.message : t("viewer.failedToLoad"));
        }
      });
    return () => {
      cancelled = true;
      controller.abort();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [view, doc?.status, doc?.id, id, fileBlob, t]);

  useEffect(() => {
    return () => {
      if (objectUrlRef.current) {
        URL.revokeObjectURL(objectUrlRef.current);
        objectUrlRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    if (view !== "preview" || !fileBlob) return;
    let cancelled = false;
    const isDocx = doc?.mime_type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
    const container = previewRef.current;
    if (isDocx && container) container.replaceChildren();
    if (isDocx) {
      if (!container) return;
      import("docx-preview")
        .then(({ renderAsync }) =>
          renderAsync(fileBlob, container).catch((err: unknown) => {
            if (!cancelled) {
              setError(err instanceof Error ? err.message : t("viewer.failedToRender"));
              setView("text");
            }
          }),
        )
        .catch(() => {
          if (!cancelled) {
            setError(t("viewer.failedToRender"));
            setView("text");
          }
        });
    } else {
      fileBlob
        .text()
        .then((text) => {
          if (!cancelled) setPreviewText(text);
        })
        .catch((err) => {
          if (!cancelled) {
            setError(err instanceof Error ? err.message : t("viewer.failedToRender"));
            setView("text");
          }
        });
    }
    return () => {
      cancelled = true;
    };
  }, [view, fileBlob, doc?.mime_type, t]);

  if (error) {
    return <p className="text-sm text-red-600 dark:text-red-400">{error}</p>;
  }

  if (!doc) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-96 w-full" />
      </div>
    );
  }

  if (doc.status !== "ready" || !pages || pages.length === 0) {
    return (
      <div className="space-y-6">
        <div className="border-b pb-5">
          <p className="text-sm text-zinc-500">
            <Link href="/documents" className="hover:underline">
              {t("nav.documents")}
            </Link>{" "}
            /
          </p>
          <h1 className="mt-1 text-3xl font-semibold tracking-tight">{doc.filename}</h1>
        </div>
        <Card className="shadow-md">
          <CardContent className="py-12 text-center">
            <p className="mb-2 text-lg font-medium">
              {doc.status === "failed" ? t("viewer.processingFailed") : t("viewer.stillProcessing")}
            </p>
            <p className="text-sm text-zinc-500">
              {doc.status === "failed" ? doc.error_message : t("viewer.availableSoon")}
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const page = pages.find((p) => p.page_number === currentPage) ?? pages[0];
  const isMember = !!workspaceId && doc.workspace_id === workspaceId;
  const canEdit = isMember && canManage(role);

  return (
    <div className="space-y-6">
      <div className="border-b pb-5">
        <p className="text-sm text-zinc-500">
          <Link href="/documents" className="hover:underline">
            {t("nav.documents")}
          </Link>{" "}
          /
        </p>
        <div className="mt-1 flex flex-wrap items-end justify-between gap-3">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-semibold tracking-tight">{doc.filename}</h1>
              <StatusBadge status={doc.status} />
              <VisibilityBadge isPublic={doc.is_public} />
            </div>
            <p className="mt-1 text-sm text-zinc-500">
              {doc.page_count} {doc.page_count === 1 ? t("documents.page") : t("documents.pages")}
            </p>
            {doc.status === "ready" && canEdit && (
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <Button variant="outline" size="sm" className="shadow-xs" onClick={toggleVisibility}>
                  {doc.is_public ? <Lock className="h-4 w-4" /> : <Globe2 className="h-4 w-4" />}
                  {doc.is_public ? t("documents.makePrivate") : t("documents.makePublic")}
                </Button>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="shadow-xs">
                      {doc.folders.length > 0 ? <Folder className="h-4 w-4" /> : <FolderInput className="h-4 w-4" />}
                      {doc.folders.length > 0 ? doc.folders.map((f) => f.name).join(", ") : t("folders.moveToFolder")}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent align="start" className="w-52">
                    <DropdownMenuLabel>{t("folders.moveToFolder")}</DropdownMenuLabel>
                    <DropdownMenuItem
                      onSelect={async () => setDoc(await documents.setFolders(doc.id, []))}
                    >
                      <Check className={doc.folders.length === 0 ? "opacity-100" : "opacity-0"} />
                      {t("folders.noFolder")}
                    </DropdownMenuItem>
                    <DropdownMenuSeparator />
                    {folders.length === 0 && <DropdownMenuItem disabled>{t("folders.createFirst")}</DropdownMenuItem>}
                    {folders.map((f) => {
                      const isIn = doc.folders.some((df) => df.id === f.id);
                      return (
                        <DropdownMenuItem
                          key={f.id}
                          onSelect={async () => setDoc(await documents.setFolders(doc.id, isIn ? [] : [f.id]))}
                        >
                          <Check className={isIn ? "opacity-100" : "opacity-0"} />
                          {f.name}
                        </DropdownMenuItem>
                      );
                    })}
                  </DropdownMenuContent>
                </DropdownMenu>
                <span className="flex flex-wrap items-center gap-1.5">
                  {doc.tags.map((tag) => (
                    <TagBadge key={tag.id} tag={tag} />
                  ))}
                </span>
                <Button variant="ghost" size="sm" onClick={() => setPickerOpen(true)}>
                  <Pencil className="h-3.5 w-3.5" />
                  {doc.tags.length === 0 ? t("tags.add") : t("tags.edit")}
                </Button>
              </div>
            )}
          </div>
          <div className="flex gap-2">
            <Button
              variant={view === "text" ? "default" : "outline"}
              size="sm"
              className={view === "text" ? "shadow-sm" : "shadow-xs"}
              onClick={() => setView("text")}
            >
              {t("viewer.text")}
            </Button>
            {doc.mime_type === "application/pdf" ? (
              <Button
                variant={view === "pdf" ? "default" : "outline"}
                size="sm"
                className={view === "pdf" ? "shadow-sm" : "shadow-xs"}
                onClick={() => setView("pdf")}
              >
                {t("viewer.pdf")}
              </Button>
            ) : (
              <Button
                variant={view === "preview" ? "default" : "outline"}
                size="sm"
                className={view === "preview" ? "shadow-sm" : "shadow-xs"}
                onClick={() => setView("preview")}
              >
                {t("viewer.preview")}
              </Button>
            )}
          </div>
        </div>
      </div>

      {view === "preview" ? (
        doc.mime_type === "application/vnd.openxmlformats-officedocument.wordprocessingml.document" ? (
          <Card className="overflow-hidden">
            <div ref={previewRef} className="docx-preview max-h-[80vh] overflow-auto bg-white p-8" />
          </Card>
        ) : (
          <Card className="overflow-hidden">
            <div className="max-h-[80vh] overflow-auto bg-white p-8">
              {previewText === null ? (
                <p className="text-sm text-zinc-500">{t("viewer.renderingPreview")}</p>
              ) : doc.mime_type === "text/markdown" ? (
                <div className="prose prose-neutral max-w-none dark:prose-invert">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{previewText}</ReactMarkdown>
                </div>
              ) : (
                <pre className="whitespace-pre-wrap font-mono text-sm leading-6 text-zinc-800">{previewText}</pre>
              )}
            </div>
          </Card>
        )
      ) : view === "text" ? (
        <Card>
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-1.5 text-sm text-zinc-500">
              {t("viewer.page")} {page.page_number}
              <Sparkles className="size-3.5 text-foreground/30" />
            </CardTitle>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="wiggle-on-hover"
                disabled={currentPage <= 1}
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              >
                <ChevronLeft className="h-4 w-4" />
              </Button>
              <span className="px-2 text-sm">
                {currentPage} / {pages.length}
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="wiggle-on-hover"
                disabled={currentPage >= pages.length}
                onClick={() => setCurrentPage((p) => Math.min(pages.length, p + 1))}
              >
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <Separator />
          <CardContent className="pt-6">
            <p className="whitespace-pre-wrap font-serif text-[15px] leading-7">{page.content}</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="overflow-hidden rounded-display">
          {pdfUrl ? (
            <iframe src={pdfUrl} className="h-[80vh] w-full" title={doc.filename} />
          ) : (
            <CardContent className="py-12 text-center text-sm text-zinc-500">{t("viewer.preparingPdf")}</CardContent>
          )}
        </Card>
      )}

      {canEdit && (
        <TagPicker
          open={pickerOpen}
          onOpenChange={setPickerOpen}
          workspaceId={workspaceId}
          documentId={doc.id}
          documentTagIds={doc.tags.map((t) => t.id)}
          onChanged={(updatedTags) => setDoc({ ...doc, tags: updatedTags })}
        />
      )}
    </div>
  );
}
