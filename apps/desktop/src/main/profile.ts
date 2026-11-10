import { existsSync, readdirSync, renameSync, rmdirSync } from "node:fs";

/** 目录条目数；不存在视为 0，其它读取错误返回 null（不接管）。 */
function directoryEntryCount(path: string): number | null {
  try {
    return readdirSync(path).length;
  } catch (error) {
    return (error as NodeJS.ErrnoException)?.code === "ENOENT" ? 0 : null;
  }
}

/**
 * 产品改名后 Electron 的 userData 目录也随之改变。首次以新名启动时接管旧目录，
 * 避免界面偏好、草稿等本地状态无故丢失；新目录已有数据时保持新目录，不回填旧数据。
 * 接管失败（跨卷、权限、正被占用）时仍使用新目录，不让启动因此失败。
 *
 * `app.getPath("userData")` 会先创建空目录，因此「存在」不等于「已有数据」：
 * 只有空目录才继续接管；删除空目录后再改名，非空或删除失败都保留新目录。
 */
export function adoptLegacyUserData(current: string, legacy: string): string {
  if (current === legacy || !existsSync(legacy)) return current;
  const entries = directoryEntryCount(current);
  if (entries === null || entries > 0) return current;
  if (existsSync(current)) {
    try {
      // 只删除空目录：`getPath` 创建的是空壳，`rename` 才能落在正确位置。
      rmdirSync(current);
    } catch {
      return current;
    }
  }
  try {
    renameSync(legacy, current);
  } catch {
    // 旧目录保留在原处：用户可见的代价是一次重新设置，而不是启动失败。
  }
  return current;
}
