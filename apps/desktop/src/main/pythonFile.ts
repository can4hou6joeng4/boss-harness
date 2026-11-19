import { statSync } from "node:fs";

/**
 * 只把普通文件（含指向文件的符号链接）视为可用路径。
 *
 * `existsSync` 对目录同样返回 true；把目录当成 Python 解释器会让 spawn 直接失败，
 * 而同一位置的 PATH 回退本来可用。目录、断链与其他文件类型一律视为不可用。
 */
export function isRegularFile(path: string): boolean {
  try {
    return statSync(path).isFile();
  } catch {
    return false;
  }
}
