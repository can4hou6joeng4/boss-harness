import { constants } from "node:fs";
import { lstat, open, rename, unlink } from "node:fs/promises";
import { dirname, join } from "node:path";
import { randomUUID } from "node:crypto";

/** 一次打开的临时文件句柄；写入、刷新、收紧权限与关闭都作用在同一 inode 上。 */
export interface SessionExportFileHandle {
  write(content: string): Promise<void>;
  sync(): Promise<void>;
  chmod(mode: number): Promise<void>;
  close(): Promise<void>;
}

/** 检查目标身份时需要的元数据；设备号加 inode 足以区分普通文件与其他条目。 */
export interface SessionExportTargetStat {
  dev: number;
  ino: number;
  /** 同一 inode 被删除重建后也可能复用编号，再核对创建 / 状态变更时间。 */
  birthtimeMs?: number;
  ctimeMs?: number;
  isFile(): boolean;
  isSymbolicLink(): boolean;
}

/** 目标身份；`null` 表示路径不存在（首次保存）。 */
export type SessionExportTargetLookup = (path: string) => Promise<SessionExportTargetStat | null>;

/**
 * 导出保存用到的文件系统操作；注入后可在不写盘的情况下覆盖失败分支。
 * 所有路径都由调用方传入；临时文件与目标同目录，确保 `rename` 是原子替换。
 */
export interface SessionExportFileSystem {
  /** 与 `fs.lstat` 相同语义：路径不存在时返回 `null`（ENOENT），不跟随符号链接。 */
  lstat: SessionExportTargetLookup;
  createTemporary(directory: string, name: string, mode: number): Promise<{ path: string; handle: SessionExportFileHandle }>;
  rename(from: string, to: string): Promise<void>;
  remove(path: string): Promise<void>;
}

/** 路径在写入期间被替换成链接或其他文件；不覆盖新 inode。 */
function targetChangedFailure(): never {
  throw new Error("targetChanged");
}

/** 比较两次 `lstat` 的身份；同时核对时间字段，排除同一 inode 被删除重建的复用。 */
function sameTarget(before: SessionExportTargetStat | null, after: SessionExportTargetStat | null): boolean {
  if (before === null || after === null) return before === after;
  return before.dev === after.dev && before.ino === after.ino &&
    (before.birthtimeMs === undefined || after.birthtimeMs === undefined || before.birthtimeMs === after.birthtimeMs) &&
    (before.ctimeMs === undefined || after.ctimeMs === undefined || before.ctimeMs === after.ctimeMs);
}

export interface SessionExportWriteOutcome {
  /**
   * 覆盖已有文件且无法收紧权限。导出改为临时文件替换后，目标总是新 inode，
   * 不会沿用旧权限，因此这里始终为 `false`；字段保留以兼容既有回执。
   */
  permissionsUnchanged: boolean;
  /** `chmod` 失败的原因；不影响保存成功，由调用方记录。 */
  permissionError?: unknown;
}

/** Windows 等平台没有 `O_NOFOLLOW`，退回普通打开；`lstat` 检查仍作为第一道防线。 */
const NO_FOLLOW = typeof constants.O_NOFOLLOW === "number" ? constants.O_NOFOLLOW : 0;

const nodeFileSystem: SessionExportFileSystem = {
  lstat: async path => {
    try {
      // `lstat` 不跟随链接，且返回设备号、inode 与时间字段供替换检查比对。
      return await lstat(path) as SessionExportTargetStat;
    } catch (error) {
      if ((error as NodeJS.ErrnoException)?.code === "ENOENT") return null;
      throw error;
    }
  },
  createTemporary: async (directory, name, mode) => {
    const path = join(directory, name);
    const handle = await open(path,
      constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | NO_FOLLOW, mode);
    return {
      path,
      handle: {
        write: content => handle.writeFile(content, "utf8"),
        sync: () => handle.sync(),
        chmod: mode => handle.chmod(mode),
        close: () => handle.close(),
      },
    };
  },
  rename: (from, to) => rename(from, to),
  remove: path => unlink(path),
};

/** `ELOOP` 与既有的 `symlink` 提示共用一条错误路径；其他 errno 原样抛出。 */
function openFailure(error: NodeJS.ErrnoException): never {
  if (error?.code === "ELOOP") throw new Error("symlink");
  throw error;
}

/** 固定前缀 + 随机后缀：足够短，不占满文件名上限，也不会与目标文件名冲突。 */
export function sessionExportTemporaryName(): string {
  return `.boss-harness-export-${randomUUID()}.tmp`;
}

/**
 * 原子写入导出文件。
 *
 * 覆盖已有导出时绝不能在写入前截断目标：先在同一目录创建唯一临时文件，
 * 写入并 `sync` 后收紧权限，关闭时再次核对目标身份，确认未换成链接或其他文件后
 * 才用 `rename` 替换目标。任何一步失败都清理临时文件并抛出原始错误，目标文件
 * 保持上一次导出的完整内容。
 * `close` 失败只关闭句柄，不覆盖已经发生的写入错误。
 */
export async function writeSessionExport(filePath: string, content: string,
                                         ops: SessionExportFileSystem = nodeFileSystem): Promise<SessionExportWriteOutcome> {
  const existing = await ops.lstat(filePath);
  if (existing?.isSymbolicLink()) throw new Error("symlink");
  // 临时文件必须与目标同目录，`rename` 才是同一文件系统内的原子替换。
  const temporary = await ops.createTemporary(dirname(filePath), sessionExportTemporaryName(), 0o600).catch(openFailure);
  let closed = false;
  try {
    await temporary.handle.write(content);
    await temporary.handle.sync();
    let permissionError: unknown;
    try {
      await temporary.handle.chmod(0o600);
    } catch (error) {
      // 临时文件本身已按 0o600 创建；收紧失败只记录，不能让整次保存失败。
      permissionError = error;
    }
    await temporary.handle.close();
    closed = true;
    // 整个写入期间目标可能被换成链接或别的文件；重命名前重新核对身份。
    // 临时文件内容已刷新，失败时只需清理它，不动目标文件。
    if (!sameTarget(existing, await ops.lstat(filePath))) targetChangedFailure();
    try {
      await ops.rename(temporary.path, filePath);
    } catch (error) {
      await ops.remove(temporary.path).catch(() => {});
      throw error;
    }
    return permissionError === undefined
      ? { permissionsUnchanged: false }
      : { permissionsUnchanged: false, permissionError };
  } finally {
    if (!closed) {
      // 失败路径：清理临时文件；关闭与删除的错误都不覆盖主错误。
      await temporary.handle.close().catch(() => {});
      await ops.remove(temporary.path).catch(() => {});
    }
  }
}
