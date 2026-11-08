import { constants } from "node:fs";
import { lstat, open } from "node:fs/promises";

/** 一次打开的导出文件句柄；写入、收紧权限与关闭都作用在同一 inode 上。 */
export interface SessionExportFileHandle {
  write(content: string): Promise<void>;
  chmod(mode: number): Promise<void>;
  close(): Promise<void>;
}

/** 导出保存用到的文件系统操作；注入后可在不写盘的情况下覆盖失败分支。 */
export interface SessionExportFileSystem {
  /** 与 `fs.lstat` 相同语义：路径不存在时抛 `ENOENT`。 */
  lstat(path: string): Promise<{ isSymbolicLink(): boolean }>;
  /**
   * 以「不跟随符号链接」的方式打开并截断文件，路径不存在时按 `mode` 创建。
   * 最终路径是符号链接时应以 `ELOOP` 失败。
   */
  openExclusive(path: string, mode: number): Promise<SessionExportFileHandle>;
}

export interface SessionExportWriteOutcome {
  /** 覆盖已有文件且 `chmod` 失败：内容已写入，但旧权限保持不变。 */
  permissionsUnchanged: boolean;
  /** `chmod` 失败的原因；新建文件也会返回以便记录，但不影响保存成功。 */
  permissionError?: unknown;
}

/** Windows 等平台没有 `O_NOFOLLOW`，退回普通打开；`lstat` 检查仍作为第一道防线。 */
const NO_FOLLOW = typeof constants.O_NOFOLLOW === "number" ? constants.O_NOFOLLOW : 0;

const nodeFileSystem: SessionExportFileSystem = {
  lstat: path => lstat(path),
  openExclusive: async (path, mode) => {
    const handle = await open(path,
      constants.O_WRONLY | constants.O_CREAT | constants.O_TRUNC | NO_FOLLOW, mode);
    return {
      write: content => handle.writeFile(content, "utf8"),
      chmod: mode => handle.chmod(mode),
      close: () => handle.close(),
    };
  },
};

/** `ELOOP` 与既有的 `symlink` 提示共用一条错误路径；其他 errno 原样抛出。 */
function openFailure(error: NodeJS.ErrnoException): never {
  if (error?.code === "ELOOP") throw new Error("symlink");
  throw error;
}

/**
 * 写入导出文件并尝试收紧权限。
 *
 * 打开时就带 `O_NOFOLLOW`，避免 `lstat` 与写入之间把目标换成符号链接。
 * `open` 的 `mode` 只对新建文件生效，覆盖已有文件时必须再对同一句柄 `chmod`。
 * 内容已经写入后，权限收紧失败不应把整次保存报成失败：返回标记由调用方提示并记录。
 */
export async function writeSessionExport(filePath: string, content: string,
                                         ops: SessionExportFileSystem = nodeFileSystem): Promise<SessionExportWriteOutcome> {
  const existing = await ops.lstat(filePath).catch((error: NodeJS.ErrnoException) => {
    if (error?.code === "ENOENT") return null;
    throw error;
  });
  if (existing?.isSymbolicLink()) throw new Error("symlink");
  const handle = await ops.openExclusive(filePath, 0o600).catch(openFailure);
  try {
    await handle.write(content);
    try {
      await handle.chmod(0o600);
      return { permissionsUnchanged: false };
    } catch (error) {
      // 新建文件已按 0o600 创建；只有覆盖已有文件时旧权限才会保留。
      return { permissionsUnchanged: existing !== null, permissionError: error };
    }
  } finally {
    await handle.close();
  }
}
