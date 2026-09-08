"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { FileText, FolderOpen } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import { TagBadge } from "@/components/tag-badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyIllustration } from "@/components/empty-illustration";
import { Sparkles, WavyUnderline } from "@/components/doodles";
import { useAuth } from "@/lib/auth-context";
import { useLanguage } from "@/lib/i18n";
import { documents, folders as foldersApi, workspaces as workspacesApi } from "@/lib/api";
import type { DocumentOut, FolderOut } from "@/lib/api";

export default function DashboardPage() {
  const { workspaceId } = useAuth();
  const { t } = useLanguage();
  const router = useRouter();
  const [docs, setDocs] = useState<DocumentOut[] | null>(null);
  const [folderCount, setFolderCount] = useState<number | null>(null);

  useEffect(() => {
    if (!workspaceId) return;
    documents
      .list(workspaceId, { limit: 5 })
      .then((res) => setDocs(res.items))
      .catch(() => setDocs([]));
    workspacesApi
      .list()
      .then(async (list) => {
        const current = list.find((w) => w.id === workspaceId) ?? list[0];
        if (!current) return setFolderCount(0);
        const folderList: FolderOut[] = await foldersApi.list(current.id);
        setFolderCount(folderList.length);
      })
      .catch(() => setFolderCount(0));
  }, [workspaceId]);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight">
          {t("dashboard.title")}
          <Sparkles className="float size-5 text-foreground/40" />
        </h1>
        <WavyUnderline className="mt-1 w-32 text-foreground/20" />
        <p className="mt-2 text-sm text-zinc-500">{t("dashboard.description")}</p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <Card className="tilt-neg tilted transition-shadow hover:shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-500">
              <span className="flex size-6 items-center justify-center rounded-md bg-muted">
                <FileText className="h-3.5 w-3.5" />
              </span>
              {t("dashboard.recentDocuments")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold tabular-nums tracking-tight">
              {docs ? docs.length : <Skeleton className="h-9 w-12" />}
            </div>
          </CardContent>
        </Card>
        <Card className="tilt-pos tilted transition-shadow hover:shadow-lg">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-500">
              <span className="flex size-6 items-center justify-center rounded-md bg-muted">
                <FolderOpen className="h-3.5 w-3.5" />
              </span>
              {t("dashboard.folders")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-4xl font-semibold tabular-nums tracking-tight">
              {folderCount !== null ? folderCount : <Skeleton className="h-9 w-12" />}
            </div>
          </CardContent>
        </Card>
        <Card className="tilt-neg tilted transition-shadow hover:shadow-lg">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-zinc-500">{t("dashboard.organize")}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="mb-3 text-sm text-zinc-500">{t("dashboard.organizeDescription")}</p>
            <Button variant="outline" size="sm" onClick={() => router.push("/documents")}>
              {t("dashboard.manageDocuments")}
            </Button>
          </CardContent>
        </Card>
      </div>

      <Card className="transition-shadow hover:shadow-md">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sm font-medium text-zinc-500">
            <span className="flex size-6 items-center justify-center rounded-md bg-muted">
              <FileText className="h-3.5 w-3.5" />
            </span>
            {t("dashboard.latestUploads")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-1.5">
          {docs === null ? (
            <>
              <Skeleton className="h-10 w-full rounded-lg" />
              <Skeleton className="h-10 w-full rounded-lg" />
            </>
          ) : docs.length === 0 ? (
            <div className="flex flex-col items-center gap-2 py-4 text-center">
              <EmptyIllustration className="mt-2" />
              <p className="text-sm text-zinc-500">{t("dashboard.noDocuments")}</p>
              <Button variant="outline" size="sm" onClick={() => router.push("/documents")}>
                {t("dashboard.uploadFirst")}
              </Button>
            </div>
          ) : (
            docs.map((doc) => (
              <button
                key={doc.id}
                type="button"
                onClick={() => router.push(`/documents/${doc.id}`)}
                className="w-full rounded-lg border border-transparent bg-card px-3 py-2 text-left shadow-xs transition-all hover:-translate-y-px hover:rotate-[0.15deg] hover:border-ring/40 hover:shadow-md"
              >
                <span className="flex items-center justify-between gap-3">
                  <span className="truncate text-sm font-medium">{doc.filename}</span>
                  <StatusBadge status={doc.status} />
                </span>
                {(doc.folders.length > 0 || doc.tags.length > 0) && (
                  <span className="mt-1 flex flex-wrap items-center gap-1.5">
                    {doc.folders.map((f) => (
                      <span key={f.id} className="text-xs text-zinc-400">
                        {f.name}
                      </span>
                    ))}
                    {doc.tags.map((tag) => (
                      <TagBadge key={tag.id} tag={tag} />
                    ))}
                  </span>
                )}
              </button>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
