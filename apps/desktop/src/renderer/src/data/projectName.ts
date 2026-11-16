import { codePointLength } from "@boss-harness/shared";

/** 本机项目显示名称上限，按 Unicode 码点计数；HTML `maxLength` 按 UTF-16 码元，需放宽到 2 倍。 */
export const PROJECT_NAME_MAX_LENGTH = 60;

/** 项目显示名称是否超过上限；超限时界面提示并禁用提交。 */
export function projectNameTooLong(name: string): boolean {
  return codePointLength(name) > PROJECT_NAME_MAX_LENGTH;
}
