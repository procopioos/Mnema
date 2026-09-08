"use client";

import Link from "next/link";

import { Card, CardContent } from "@/components/ui/card";
import { useLanguage } from "@/lib/i18n";
import { CornerSparkle, Sparkles, WavyUnderline } from "@/components/doodles";

const SECTIONS = ["collection", "use", "sharing", "cookies", "retention", "rights", "contact"] as const;

export default function PrivacyPage() {
  const { t } = useLanguage();

  return (
    <div className="flex flex-1 items-start justify-center bg-gradient-to-b from-muted/60 to-background p-4 md:p-8">
      <div className="w-full max-w-3xl">
        <h1 className="flex items-center gap-2 text-3xl font-semibold tracking-tight">
          {t("privacy.title")}
          <Sparkles className="size-5 text-foreground/40" />
        </h1>
        <WavyUnderline className="mt-1 w-40 text-foreground/20" />
        <p className="mt-2 text-sm text-zinc-500">{t("privacy.lastUpdated")}</p>

        <div className="mt-6 space-y-4">
          {SECTIONS.map((section) => (
            <Card key={section} className="relative shadow-sm">
              <CardContent className="space-y-2">
                <h2 className="text-lg font-semibold tracking-tight">{t(`privacy.${section}.title`)}</h2>
                <p className="text-sm leading-6 text-zinc-600 dark:text-zinc-300">{t(`privacy.${section}.body`)}</p>
              </CardContent>
            </Card>
          ))}
        </div>

        <p className="mt-4 text-xs italic leading-5 text-zinc-500 dark:text-zinc-400">{t("privacy.punchline")}</p>

        <p className="mt-8 text-sm text-zinc-500">
          <Link href="/" className="underline-offset-4 hover:underline">
            {t("nav.dashboard")}
          </Link>
        </p>
      </div>
    </div>
  );
}