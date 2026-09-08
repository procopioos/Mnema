"use client";

import { useLanguage } from "@/lib/i18n";
import { ROLE_LABEL_KEY } from "@/lib/roles";
import type { Role } from "@/lib/api";

const ROLE_STYLES: Record<Role, string> = {
  owner: "border-amber-500/40 bg-amber-500/10 text-amber-700 dark:text-amber-300",
  admin: "border-violet-500/40 bg-violet-500/10 text-violet-700 dark:text-violet-300",
  manager: "border-sky-500/40 bg-sky-500/10 text-sky-700 dark:text-sky-300",
  employee: "border-zinc-500/40 bg-zinc-500/10 text-zinc-600 dark:text-zinc-300",
};

export function RoleBadge({ role }: { role: Role }) {
  const { t } = useLanguage();
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium capitalize ${ROLE_STYLES[role]}`}
    >
      {t(ROLE_LABEL_KEY[role])}
    </span>
  );
}