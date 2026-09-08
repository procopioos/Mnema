import type { Role } from "./api";
import type { TranslationKey } from "./translations/en";

export const ROLE_LABEL_KEY: Record<Role, TranslationKey> = {
  owner: "role.owner",
  admin: "role.admin",
  manager: "role.manager",
  employee: "role.employee",
};

export const ROLE_RANK: Record<Role, number> = {
  owner: 4,
  admin: 3,
  manager: 2,
  employee: 1,
};

export function canManage(role: Role | null | undefined): boolean {
  return role != null && ROLE_RANK[role] >= ROLE_RANK.manager;
}

export function canAdmin(role: Role | null | undefined): boolean {
  return role != null && ROLE_RANK[role] >= ROLE_RANK.admin;
}