import type { AuditAction } from "./api";
import type { TranslationKey } from "./translations/en";

export const AUDIT_ACTION_LABEL_KEY: Record<AuditAction, TranslationKey> = {
  "document.view": "audit.action.document.view",
  "document.download": "audit.action.document.download",
  "document.upload": "audit.action.document.upload",
  "document.delete": "audit.action.document.delete",
  "document.visibility": "audit.action.document.visibility",
  "workspace.member.add": "audit.action.workspace.member.add",
  "workspace.member.remove": "audit.action.workspace.member.remove",
  "workspace.member.role": "audit.action.workspace.member.role",
  "auth.login": "audit.action.auth.login",
  "admin.reset": "audit.action.admin.reset",
  "admin.user.update": "audit.action.admin.user.update",
  "admin.workspace.create": "audit.action.admin.workspace.create",
  "admin.workspace.rename": "audit.action.admin.workspace.rename",
  "admin.workspace.delete": "audit.action.admin.workspace.delete",
  "admin.workspace.quota": "audit.action.admin.workspace.quota",
  "admin.workspace.regenerate_code": "audit.action.admin.workspace.regenerate_code",
  "workspace.member.move": "audit.action.workspace.member.move",
};

export function formatAuditTime(value: string): string {
  return new Date(value).toLocaleString();
}