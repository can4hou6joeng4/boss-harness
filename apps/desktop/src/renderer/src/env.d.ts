/// <reference types="vite/client" />

import type { BossBridge } from "../../preload/bridge";

declare global {
  /** 构建时由 electron-vite 注入的发布版本号。 */
  const __APP_VERSION__: string;

  interface Window {
    /** preload 的桥接面与实现共用 bridge.ts 的 BossBridge，不再单独维护方法列表。 */
    boss: BossBridge;
  }
}

export {};
