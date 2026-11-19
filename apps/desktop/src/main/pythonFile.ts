import { accessSync, constants, statSync } from "node:fs";

/**
 * 默认虚拟环境解释器须为有执行权限的普通文件；符号链接按目标判断。
 * 不启动候选，也不验证其内容、Python 版本或内核依赖。
 */
export function isExecutableFile(path: string): boolean {
  try {
    if (!statSync(path).isFile()) return false;
    accessSync(path, constants.X_OK);
    return true;
  } catch {
    return false;
  }
}
