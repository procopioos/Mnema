"use client";

import { LayoutGrid, Rows3 } from "lucide-react";

import { useLanguage } from "@/lib/i18n";

export type ViewMode = "list" | "grid";

export function ViewToggle({ value, onChange }: { value: ViewMode; onChange: (mode: ViewMode) => void }) {
  const { t } = useLanguage();
  const base = "flex size-7 items-center justify-center rounded-md transition-colors";
  return (
    <div
      role="group"
      aria-label={t("documents.viewToggle")}
      className="flex items-center gap-0.5 rounded-lg border bg-card p-0.5 shadow-xs"
    >
      <button
        type="button"
        aria-pressed={value === "list"}
        aria-label={t("documents.viewList")}
        onClick={() => onChange("list")}
        className={`${base} ${value === "list" ? "bg-muted text-foreground" : "text-zinc-400 hover:text-foreground"}`}
      >
        <Rows3 className="h-4 w-4" />
      </button>
      <button
        type="button"
        aria-pressed={value === "grid"}
        aria-label={t("documents.viewGrid")}
        onClick={() => onChange("grid")}
        className={`${base} ${value === "grid" ? "bg-muted text-foreground" : "text-zinc-400 hover:text-foreground"}`}
      >
        <LayoutGrid className="h-4 w-4" />
      </button>
    </div>
  );
}