import type { SessionExportSaveResult } from "@boss-harness/protocol";

/**
 * 导出回执校验：统计必须完整，且已导出回合数不能超过视图声明的总回合数。
 * `exportedTurnCount` 是导出内容中 `kind == "turn"` 的单元数，内核从同一组回合构造，
 * 大于 `turnCount` 说明回执自相矛盾，不能展示成导出统计。
 */
export function savedExportResult(value: unknown): SessionExportSaveResult | null {
  if (!value || typeof value !== "object") return null;
  const raw = value as Record<string, unknown>;
  if (raw.saved === false && raw.canceled === true) return { saved: false, canceled: true };
  const counts = raw.redactions as Record<string, unknown> | undefined;
  const count = (item: unknown): item is number => typeof item === "number" && Number.isSafeInteger(item) && item >= 0;
  if (raw.saved !== true || typeof raw.fileName !== "string" || !raw.fileName || raw.fileName.length > 255 ||
    !count(raw.bytes) || typeof raw.truncated !== "boolean") return null;
  const turnCount = raw.turnCount, exportedTurnCount = raw.exportedTurnCount;
  if (!count(turnCount) || !count(exportedTurnCount) || exportedTurnCount > turnCount ||
    (raw.toolResults !== "omitted" && raw.toolResults !== "included") || !counts ||
    (raw.permissionsUnchanged !== undefined && typeof raw.permissionsUnchanged !== "boolean") ||
    !["secrets", "environment", "paths", "personalInfo"].every(key => count(counts[key]))) return null;
  return value as SessionExportSaveResult;
}
