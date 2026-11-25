/**
 * 系统通知的引用保留。
 *
 * Electron 的 `Notification` 由 JS 对象弱持有：对象被垃圾回收后，`click` 监听不再触发，
 * 通知也可能从通知中心消失。保留最近若干条引用，直到通知关闭或显示失败。
 */
export interface RetainableNotification {
  show(): void;
  close?(): void;
  once(event: "close" | "failed", listener: () => void): unknown;
}

export const NOTIFICATION_RETENTION_LIMIT = 32;

export class NotificationRegistry {
  private readonly retained = new Set<RetainableNotification>();
  private readonly byKey = new Map<string, RetainableNotification>();
  private readonly limit: number;

  constructor(limit: number = NOTIFICATION_RETENTION_LIMIT) {
    if (!Number.isSafeInteger(limit) || limit < 1) throw new Error("通知保留上限必须是正整数");
    this.limit = limit;
  }

  #forget(notification: RetainableNotification): boolean {
    let hadKey = false;
    for (const [key, value] of this.byKey) {
      if (value !== notification) continue;
      this.byKey.delete(key);
      hadKey = true;
    }
    return hadKey;
  }

  /** 保留并显示通知；重复显示同一对象或同一个 key 时重新排到最新，避免被当成最旧的一条淘汰。 */
  show(notification: RetainableNotification, key?: string): void {
    this.retained.delete(notification);
    this.retained.add(notification);
    if (key) {
      const previous = this.byKey.get(key);
      if (previous && previous !== notification) {
        this.retained.delete(previous);
        this.#forget(previous);
        try { previous.close?.(); } catch {}
      }
      this.byKey.set(key, notification);
    }
    while (this.retained.size > this.limit) {
      const oldest = this.retained.values().next().value;
      if (oldest === undefined) break;
      this.retained.delete(oldest);
      // 带 key 的卡片被淘汰后无法按审批事件关闭，因此在释放 key 时主动关闭。
      if (this.#forget(oldest)) {
        try { oldest.close?.(); } catch {}
      }
    }
    const release = (): void => {
      this.retained.delete(notification);
      if (key && this.byKey.get(key) === notification) this.byKey.delete(key);
    };
    notification.once("close", release);
    notification.once("failed", release);
    try {
      notification.show();
    } catch (error) {
      // 平台显示失败时不会发出 close / failed；立即释放保留位与 key 路由，再抛出原错误。
      release();
      throw error;
    }
  }

  /** 主动关闭一个带 key 的通知；审批已经结算或路由失效后不再留在通知中心。 */
  dismiss(key: string): boolean {
    const notification = this.byKey.get(key);
    if (!notification) return false;
    this.byKey.delete(key);
    this.retained.delete(notification);
    try { notification.close?.(); } catch {}
    return true;
  }

  /** 按前缀关闭通知，用于断开时一次撤销同一会话的全部审批提醒。 */
  dismissPrefix(prefix: string): number {
    let count = 0;
    for (const key of [...this.byKey.keys()]) {
      if (key.startsWith(prefix) && this.dismiss(key)) count += 1;
    }
    return count;
  }

  /** 当前保留的通知数量；供诊断与离线探针使用。 */
  get size(): number {
    return this.retained.size;
  }
}
