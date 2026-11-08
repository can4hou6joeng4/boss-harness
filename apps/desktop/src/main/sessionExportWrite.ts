import { chmod, lstat, writeFile } from "node:fs/promises";

/** 导出保存用到的文件系统操作；注入后可在不写盘的情况下覆盖失败分支。 */
export interface SessionExportFileSystem {
  /** 与 `fs.lstat` 相同语义：路径不存在时抛 `ENOENT`。 */
  lstat(path: string): Promise<{ isSymbolicLink(): boolean }>;
  writeFile(path: string, content: string, options: { encoding: "utf8"; mode: number }): Promise<void>;
  chmod(path: string, mode: number): Promise<void>;
}

export interface SessionExportWriteOutcome {
  /** 覆盖已有文件且 `chmod` 失败：内容已写入，但旧权限保持不变。 */
  permissionsUnchanged: boolean;
  /** `chmod` 失败的原因；新建文件也会返回以便记录，但不影响保存成功。 */
  permissionError?: unknown;
}

const nodeFileSystem: SessionExportFileSystem = {
  lstat: path => lstat(path),
  writeFile: (path, content, options) => writeFile(path, content, options),
  chmod: (path, mode) => chmod(path, mode),
};

/**
 * 写入导出文件并尝试收紧权限。
 *
 * `writeFile` 的 `mode` 只对新建文件生效，覆盖已有文件时必须再 `chmod`。
 * 内容已经写入后，权限收紧失败不应把整次保存报成失败：返回标记由调用方提示并记录。
 */
export async function writeSessionExport(filePath: string, content: string,
                                         ops: SessionExportFileSystem = nodeFileSystem): Promise<SessionExportWriteOutcome> {
  const existing = await ops.lstat(filePath).catch((error: NodeJS.ErrnoException) => {
    if (error?.code === "ENOENT") return null;
    throw error;
  });
  if (existing?.isSymbolicLink()) throw new Error("symlink");
  await ops.writeFile(filePath, content, { encoding: "utf8", mode: 0o600 });
  try {
    await ops.chmod(filePath, 0o600);
    return { permissionsUnchanged: false };
  } catch (error) {
    // 新建文件已按 0o600 创建；只有覆盖已有文件时旧权限才会保留。
    return { permissionsUnchanged: existing !== null, permissionError: error };
  }
}
