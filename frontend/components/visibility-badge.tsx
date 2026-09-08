"use client";

import { Globe2, Lock } from "lucide-react";

import { useLanguage } from "@/lib/i18n";

export function VisibilityBadge({ isPublic }: { isPublic: boolean }) {
  const { t } = useLanguage();
  const base =
    "inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[10px] font-medium tracking-wide";
  if (isPublic) {
    return (
      <span
        className={`${base} border-sky-300/70 bg-sky-500/10 text-sky-700 dark:border-sky-500/40 dark:bg-sky-400/10 dark:text-sky-300`}
        title={t("documents.visibility")}
      >
        <Globe2 className="h-3 w-3" />
        {t("documents.publicDoc")}
      </span>
    );
  }
  return (
    <span
      className={`${base} border-zinc-300/80 bg-zinc-500/5 text-zinc-500 dark:border-zinc-700 dark:bg-zinc-400/10 dark:text-zinc-400`}
      title={t("documents.visibility")}
    >
      <Lock className="h-3 w-3" />
      {t("documents.privateDoc")}
    </span>
  );
}