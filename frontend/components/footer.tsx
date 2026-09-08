"use client";

import Link from "next/link";

import { useLanguage } from "@/lib/i18n";
import { WavyDivider } from "@/components/doodles";

export function Footer() {
  const { t } = useLanguage();

  return (
    <footer className="relative border-t bg-background/70 backdrop-blur-xl dark:bg-background/70">
      <WavyDivider className="pointer-events-none absolute inset-x-0 -top-1.5 h-3 w-full text-foreground/[0.03]" />
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <p className="text-sm text-zinc-500">{t("common.copyright")}</p>
        <Link
          href="/privacy"
          className="text-sm text-zinc-600 underline-offset-4 hover:underline dark:text-zinc-400 dark:hover:text-zinc-100"
        >
          {t("privacy.title")}
        </Link>
      </div>
    </footer>
  );
}