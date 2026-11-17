import type { EventListResponse, ItemContentReference, ItemContentReadResponse, ItemListResponse, ThreadItem, ThreadReadResponse } from "@boss-harness/protocol";
import { safeSlice, stripIpcErrorWrapper } from "@boss-harness/shared";
import { throwIfHarnessRpcError } from "./harnessRpcErrors";
import type { HarnessEvent } from "./harnessEvents";
import { trackCursor } from "./cursorChain";
import { assertSnapshotRouteFields, threadSnapshotOf } from "./snapshotShape";

interface Api { request<T>(method: string, params?: unknown): Promise<T> }
/** 单次恢复允许的分页上限：只兜住异常内核造成的无尽翻页，正常会话远达不到。 */
const MAX_PAGE_COUNT = 10_000;
const MAX_CURSOR_LENGTH = 2048;
const ITEM_ID_LIMIT = 200;
/** 正文分段读取的最小合理粒度：异常内核用 1 个码点分页时，不能把恢复拖成数百万次请求。 */
const MIN_CONTENT_CHUNK_CHARS = 1024;
/** 一次恢复允许的正文分页请求总量：异常内核用大量小条目也能把恢复拖成百万次请求。 */
const MAX_CONTENT_PAGE_READS = 10_000;

interface ContentReadBudget { pages: number }
const STALE_CONTENT_RECHECK_NOTICE = "会话内容版本已变化，请重新打开会话并核对当前引用后查看";

type HarnessRpcError = Error & { code?: unknown; data?: unknown; rpcError?: boolean };

function staleContentError(error: unknown): string | null {
  const rpc = error as HarnessRpcError;
  if (!rpc || rpc.rpcError !== true || rpc.code !== -32011) return null;
  const data = rpc.data;
  if (!data || typeof data !== "object") return null;
  const record = data as Record<string, unknown>;
  if (record.code !== "STALE_CONTENT") return null;
  const ref = record.currentRef;
  if (!ref || typeof ref !== "object") return null;
  try {
    validateContentReference(ref as ItemContentReference);
  } catch {
    return null;
  }
  return STALE_CONTENT_RECHECK_NOTICE;
}

/** 分页条目必须带可用于定位与合并的标识；原始值、数组与空 id 都不能进入快照。 */
function threadItemId(value: unknown): string | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) return null;
  const id = (value as { id?: unknown }).id;
  return typeof id === "string" && id.length > 0 && id.length <= ITEM_ID_LIMIT ? id : null;
}

/** 冻结快照声明的条目总数；旧内核缺省，存在但非法时整体拒绝。 */
function snapshotItemCount(value: unknown): number | undefined {
  if (value === undefined) return undefined;
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) {
    throw new Error("会话快照条目计数无效");
  }
  return value;
}
function validateContentReference(reference: ItemContentReference): void {
  if (!reference || reference.encoding !== "text" || typeof reference.sha256 !== "string" || !/^[a-f0-9]{64}$/.test(reference.sha256) ||
      typeof reference.itemId !== "string" || !/^[a-zA-Z0-9][a-zA-Z0-9_-]{0,127}$/.test(reference.itemId) ||
      typeof reference.threadId !== "string" || !/^[a-f0-9]{12}$/.test(reference.threadId) ||
      (reference.part !== "text" && reference.part !== "thinking") ||
      (reference.snapshotId !== undefined && (typeof reference.snapshotId !== "string" || !/^[a-f0-9]{32}$/.test(reference.snapshotId))) ||
      !Number.isSafeInteger(reference.characterLength) || !Number.isSafeInteger(reference.byteLength) ||
      reference.characterLength < 1 || reference.byteLength < reference.characterLength ||
      reference.byteLength > reference.characterLength * 4 || reference.byteLength > 16 * 1024 * 1024) {
    throw new Error("会话内容引用无效或超出自动恢复上限");
  }
}
function cursor(event: HarnessEvent): bigint | null {
  const value = event.params?.eventCursor;
  return typeof value === "string" && /^\d{1,19}$/.test(value) ? BigInt(value) : null;
}

/** Snapshot + ordered replay; subscriptions stay live while history pages load. */
export class HarnessReplica {
  private readonly cursors = new Map<string, bigint>();
  private readonly loading = new Map<string, { buffered: HarnessEvent[]; flight: Promise<ThreadReadResponse | null> }>();
  private epoch = 0;
  private readonly generations = new Map<string, number>();
  private readonly itemVersions = new Map<string, number>();
  /** 每个会话最近一次恢复失败的具体原因；调用方用它替代通用文案。 */
  private readonly failures = new Map<string, string>();
  private nextItemVersion = 0;
  private readonly api: Api;
  private readonly onEvent: (event: HarnessEvent) => void;
  private readonly onSnapshot: (snapshot: ThreadReadResponse) => void;
  /** 内核声明 sessionBranchViews 时为真：已分支的会话改按当前分支（view=branch）读取。 */
  private readonly branchViews: () => boolean;
  /** 内核另声明 sessionBranchSnapshots 时为真：分支视图也用冻结快照分页，条目与事件游标同一切点。 */
  private readonly branchSnapshots: () => boolean;
  constructor(api: Api, onEvent: (event: HarnessEvent) => void, onSnapshot: (snapshot: ThreadReadResponse) => void,
    branchViews: () => boolean = () => false, branchSnapshots: () => boolean = () => false) {
    this.api = api; this.onEvent = onEvent; this.onSnapshot = onSnapshot; this.branchViews = branchViews;
    this.branchSnapshots = branchSnapshots;
  }

  /** 分支指针移动后重新读取；若已有读取在途，等它结束后再读一次，避免沿用切换前的快照。 */
  reload(threadId: string): Promise<ThreadReadResponse | null> {
    const existing = this.loading.get(threadId);
    return existing ? existing.flight.then(() => this.resume(threadId)) : this.resume(threadId);
  }

  /**
   * 当前分支的冻结快照：thread/resume snapshot=true view=branch 在同一切点固定条目与事件游标，
   * 分页期间新到的增量只经事件重放应用一次（未分支的会话等同日志快照）。分支指针在分页中移动时
   * 内核返回 SNAPSHOT_LEAF_CHANGED，这里重新取快照，最多重试两次。
   */
  private async frozenBranchSnapshot(threadId: string, current: () => void,
    budget: ContentReadBudget = { pages: 0 }): Promise<ThreadReadResponse> {
    for (let attempt = 0; ; attempt += 1) {
      try {
        const snapshot = await this.api.request<ThreadReadResponse>("thread/resume", { threadId, excludeTurns: true, snapshot: true, view: "branch" });
        current();
        if (snapshot.view !== "branch" || !snapshot.branch || snapshot.branch.threadId !== threadId || snapshot.thread?.id !== threadId ||
            typeof snapshot.snapshotId !== "string" || !/^[a-f0-9]{32}$/.test(snapshot.snapshotId)) throw new Error("分支快照响应无效");
        assertSnapshotRouteFields(snapshot.thread);
        const snapshotId = snapshot.snapshotId;
        const items = await this.readAllItems(
          pageCursor => ({ threadId, snapshotId, view: "branch", cursor: pageCursor, limit: 100 }),
          current, snapshotItemCount(snapshot.itemCount));
        const hydrated: ThreadItem[] = [];
        for (const item of items) { current(); hydrated.push(await this.resolveItemContent(item, threadId, snapshotId, current, budget)); }
        snapshot.items = hydrated;
        return snapshot;
      } catch (error) {
        if (attempt >= 2 || !(error instanceof Error) || !/SNAPSHOT_LEAF_CHANGED|分支指针已变化/.test(error.message)) throw error;
        current();
      }
    }
  }

  /**
   * 已分支会话的当前分支投影。内核声明 sessionBranchSnapshots 时走冻结快照；更早的内核
   * 优先用一次性的 thread/read（条目与事件游标同锁读取），响应过大时退回按分支分页读取条目
   * （该兼容路径无冻结切点，运行中打开可能短暂重复流式内容，回合结束后重新读取会纠正）。
   */
  private async branchSnapshot(threadId: string, current: () => void,
    budget: ContentReadBudget = { pages: 0 }): Promise<ThreadReadResponse | null> {
    if (!this.branchViews()) return null;
    if (this.branchSnapshots()) return this.frozenBranchSnapshot(threadId, current, budget);
    const probe = await this.api.request<ThreadReadResponse>("thread/read", { threadId, excludeTurns: true, view: "branch" });
    current();
    if (probe.view !== "branch" || !probe.branch || probe.branch.threadId !== threadId) throw new Error("分支视图响应无效");
    if (!probe.branch.branched) return null;
    let snapshot: ThreadReadResponse;
    try {
      snapshot = await this.api.request<ThreadReadResponse>("thread/read", { threadId, view: "branch" });
    } catch (error) {
      if (!(error instanceof Error) || !/RESPONSE_TOO_LARGE|会话响应过大/.test(error.message)) throw error;
      current();
      snapshot = probe;
      snapshot.items = await this.readAllItems(
        pageCursor => ({ threadId, view: "branch", cursor: pageCursor, limit: 100 }), current);
    }
    current();
    if (snapshot.view !== "branch" || snapshot.thread?.id !== threadId) throw new Error("分支视图响应无效");
    // 与 `thread/resume` 普通路径同一契约：线路字段会被渲染期展示与 `toLowerCase()` 使用，
    // 条目必须可枚举；畸形回执让该会话显示恢复失败，而不是在渲染时落入应用级错误边界。
    assertSnapshotRouteFields(snapshot.thread);
    if (!Array.isArray(snapshot.items)) throw new Error("分支视图条目无效");
    const hydrated: ThreadItem[] = [];
    for (const item of snapshot.items) { current(); hydrated.push(await this.resolveItemContent(item, threadId, undefined, current, budget)); }
    snapshot.items = hydrated;
    return snapshot;
  }

  invalidate(): void {
    this.epoch += 1;
    this.loading.clear();
    this.cursors.clear();
    this.generations.clear();
    this.itemVersions.clear();
    this.failures.clear();
  }

  ingest(event: HarnessEvent): void {
    const id = event.params?.threadId;
    if (id && this.loading.has(id)) { this.loading.get(id)!.buffered.push(event); return; }
    this.apply(event);
  }

  private apply(event: HarnessEvent): void {
    const id = event.params?.threadId, value = cursor(event);
    if (id && value !== null) {
      if (value <= (this.cursors.get(id) ?? -1n)) return;
      this.cursors.set(id, value);
    }
    const itemId = event.params?.itemId;
    const key = id && itemId ? `${id}\0${itemId}` : undefined;
    const version = ++this.nextItemVersion;
    if (key) this.itemVersions.set(key, version);
    const epoch = this.epoch;
    const generation = id ? this.generations.get(id) : undefined;
    this.onEvent(event);
    if (event.method === "item/completed" && (event.params?.textRef || event.params?.thinkingRef)) {
      const current = () => {
        if (epoch !== this.epoch || (id && this.generations.get(id) !== generation) ||
            (key && this.itemVersions.get(key) !== version)) throw new Error("内容加载已过期");
      };
      void this.resolveEventContent(event, current).then(content => {
        current();
        this.onEvent({ ...event, params: { ...event.params, ...content } });
      }).catch(error => {
        try { current(); this.reportFailure(id ?? "", error); } catch { /* newer state owns it */ }
      });
    }
  }

  resume(threadId: string): Promise<ThreadReadResponse | null> {
    const existing = this.loading.get(threadId);
    if (existing) return existing.flight;
    const epoch = this.epoch, buffered: HarnessEvent[] = [];
    const generation = (this.generations.get(threadId) ?? 0) + 1;
    this.generations.set(threadId, generation);
    for (const key of this.itemVersions.keys()) if (key.startsWith(`${threadId}\0`)) this.itemVersions.delete(key);
    const current = () => {
      if (epoch !== this.epoch || this.generations.get(threadId) !== generation) throw new Error("会话恢复已过期");
    };
    const flight = Promise.resolve().then(async () => {
      current();
      const contentBudget: ContentReadBudget = { pages: 0 };
      const branched = await this.branchSnapshot(threadId, current, contentBudget);
      // 普通路径没有分支投影的 view/branch 字段可核对；回执必须属于请求的会话，
      // 否则消息与线路会被写到另一个会话。
      const snapshot = branched ?? threadSnapshotOf(
        await this.api.request<ThreadReadResponse>("thread/resume", { threadId, excludeTurns: true, snapshot: true }), threadId);
      current();
      if (branched) {
        // Items were read together with the branch projection above.
      } else if (snapshot.snapshotId) {
        const snapshotId = snapshot.snapshotId;
        const items = await this.readAllItems(
          pageCursor => ({ threadId, snapshotId, cursor: pageCursor, limit: 100 }),
          current, snapshotItemCount(snapshot.itemCount));
        const hydrated: ThreadItem[] = [];
        for (const item of items) { current(); hydrated.push(await this.resolveItemContent(item, threadId, snapshot.snapshotId, current, contentBudget)); }
        snapshot.items = hydrated;
      } else {
        // Compatibility with 0.1 servers that do not expose stable snapshot pages.
        const full = threadSnapshotOf(await this.api.request<ThreadReadResponse>("thread/read", { threadId }), threadId);
        current();
        const hydrated: ThreadItem[] = [];
        for (const item of full.items) { current(); hydrated.push(await this.resolveItemContent(item, threadId, undefined, current, contentBudget)); }
        snapshot.items = hydrated;
      }
      const eventCursor = snapshot.eventCursor;
      if (eventCursor !== undefined && (typeof eventCursor !== "string" || !/^\d{1,19}$/.test(eventCursor))) {
        throw new Error("会话事件游标无效");
      }
      current();
      this.failures.delete(threadId);
      this.onSnapshot(snapshot);
      const after = eventCursor ?? "0";
      this.cursors.set(threadId, BigInt(after));
      if (eventCursor !== undefined) await this.replayEvents(threadId, after, current);
      current();
      return snapshot;
    }).catch(error => {
      try { current(); this.reportFailure(threadId, error); } catch { /* superseded recovery */ }
      return null;
    }).finally(() => {
      if (epoch === this.epoch && this.generations.get(threadId) === generation) {
        buffered.sort((a, b) => { const x = cursor(a) ?? 0n, y = cursor(b) ?? 0n; return x < y ? -1 : x > y ? 1 : 0; });
        for (const event of buffered) this.apply(event);
      }
      if (this.loading.get(threadId)?.flight === flight) this.loading.delete(threadId);
    });
    this.loading.set(threadId, { buffered, flight });
    return flight;
  }

  /** 分页读满条目列表；形状、游标前进与页数都要校验，异常响应让恢复失败而不是无限翻页。 */
  private async readAllItems(
    params: (cursor: string | null) => Record<string, unknown>,
    current: () => void,
    expectedCount?: number,
  ): Promise<ThreadItem[]> {
    const items: ThreadItem[] = [];
    const seen = new Set<string>();
    const seenIds = new Set<string>();
    let cursor: string | null = null;
    for (let pages = 0; ; pages += 1) {
      if (pages >= MAX_PAGE_COUNT) throw new Error("会话条目分页过多，未能完整读取");
      const page: ItemListResponse = await this.api.request("thread/items/list", params(cursor));
      current();
      if (!page || !Array.isArray(page.items)) throw new Error("会话条目分页响应无效");
      const next: string | null = page.nextCursor ?? null;
      if (next !== null && (typeof next !== "string" || !next || next.length > MAX_CURSOR_LENGTH)) {
        throw new Error("会话条目分页游标无效");
      }
      if (next !== null) trackCursor(seen, next, "会话条目");
      for (const entry of page.items) {
        const id = threadItemId(entry);
        if (id === null) throw new Error("会话条目缺少有效标识");
        // 同一条记录只能出现一次；重复 id 会让消息定位与本地状态合并无法区分条目。
        if (seenIds.has(id)) throw new Error(`会话条目标识重复：${safeSlice(id, 40)}`);
        seenIds.add(id);
        items.push(entry);
      }
      if (next === null) {
        // 冻结快照的条目数固定；提前结束或多读都说明历史不完整，不能静默展示。
        if (expectedCount !== undefined && items.length !== expectedCount) {
          throw new Error(`会话快照条目数不一致：声明 ${expectedCount} 个，实际读取 ${items.length} 个`);
        }
        return items;
      }
      cursor = next;
    }
  }

  /** 按事件游标重放增量，同样校验形状与游标前进，避免异常响应让恢复一直转圈。 */
  private async replayEvents(threadId: string, start: string, current: () => void): Promise<void> {
    let cursor = start;
    const seen = new Set<string>([start]);
    for (let pages = 0; ; pages += 1) {
      if (pages >= MAX_PAGE_COUNT) throw new Error("会话事件分页过多，未能完整重放");
      const page: EventListResponse = await this.api.request("event/list", { threadId, cursor, limit: 200 });
      current();
      if (!page || !Array.isArray(page.events)) throw new Error("会话事件分页响应无效");
      const next = page.nextCursor;
      if (typeof next !== "string" || !next || next.length > MAX_CURSOR_LENGTH) {
        throw new Error("会话事件分页游标无效");
      }
      const more = page.hasMore === true;
      // 还有下一页却没有新事件、或游标重复：再请求只会得到同一批页。
      if (more) {
        if (page.events.length === 0) throw new Error("会话事件分页未前进");
        trackCursor(seen, next, "会话事件");
      }
      for (const event of page.events) this.apply(event as HarnessEvent);
      if (!more) return;
      cursor = next;
    }
  }

  /** 最近一次恢复失败的原因（已含处理建议）；成功恢复或连接作废后清除。 */
  lastFailure(threadId: string): string | undefined {
    return this.failures.get(threadId);
  }

  private reportFailure(threadId: string, error: unknown): void {
    // 非保留错误码的方法会由主进程抛出，Electron 在渲染层拼接 IPC 包装；提示只保留真实原因。
    const stale = staleContentError(error);
    const detail = stale ?? (error instanceof Error ? safeSlice(stripIpcErrorWrapper(error.message), 300) : "响应无效");
    const message = `读取会话内容失败：${detail}。已保留当前内容，请重新打开会话重试。`;
    if (threadId) this.failures.set(threadId, message);
    this.onEvent({ method: "session/error", params: { threadId, message } });
  }

  private async readContent(reference: ItemContentReference, current: () => void,
    budget?: ContentReadBudget): Promise<string> {
    current();
    validateContentReference(reference);
    let cursor: string | undefined;
    let offset = 0;
    let byteLength = 0;
    let text = "";
    const pageLimit = Math.min(MAX_PAGE_COUNT,
      Math.ceil(reference.characterLength / MIN_CONTENT_CHUNK_CHARS) + 8);
    let pages = 0;
    while (true) {
      if (pages >= pageLimit) throw new Error("会话内容分段过多，未能完整读取");
      if (budget) {
        if (budget.pages >= MAX_CONTENT_PAGE_READS) throw new Error("本次恢复的大正文分页过多，未能完整读取");
        budget.pages += 1;
      }
      pages += 1;
      const response = throwIfHarnessRpcError(await this.api.request<ItemContentReadResponse>("thread/item/content/read", {
        threadId: reference.threadId, itemId: reference.itemId, part: reference.part,
        sha256: reference.sha256, snapshotId: reference.snapshotId, cursor, limit: 16384,
      }));
      current();
      const actual = response.contentRef;
      if (!actual || (["threadId", "itemId", "part", "encoding", "sha256", "byteLength", "characterLength", "snapshotId"] as const)
        .some(key => actual[key] !== reference[key])) throw new Error("会话内容版本已变化");
      if (response.offset !== offset || typeof response.text !== "string" || response.text.length > 32768) {
        throw new Error("会话内容分段无效");
      }
      const length = Array.from(response.text).length;
      if (length < 1 || length > 16384) throw new Error("会话内容分段长度无效");
      const chunkBytes = new TextEncoder().encode(response.text).byteLength;
      if (offset + length > reference.characterLength || byteLength + chunkBytes > reference.byteLength) {
        throw new Error("会话内容分段超过引用长度");
      }
      text += response.text;
      offset += length;
      byteLength += chunkBytes;
      if (response.nextCursor === null) break;
      if (typeof response.nextCursor !== "string" || !response.nextCursor.startsWith("ic1_") ||
          response.nextCursor.length > 2048 || response.nextCursor === cursor || offset >= reference.characterLength) {
        throw new Error("会话内容游标无效");
      }
      cursor = response.nextCursor;
    }
    const bytes = new TextEncoder().encode(text);
    current();
    if (offset !== reference.characterLength || bytes.byteLength !== reference.byteLength) {
      throw new Error("会话内容长度校验失败");
    }
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", bytes));
    current();
    const sha256 = Array.from(digest, byte => byte.toString(16).padStart(2, "0")).join("");
    if (sha256 !== reference.sha256) throw new Error("会话内容摘要校验失败");
    return text;
  }

  private async resolveItemContent(item: ThreadItem, threadId: string, snapshotId: string | undefined,
    current: () => void, budget?: ContentReadBudget): Promise<ThreadItem> {
    const resolved = { ...item };
    for (const part of ["text", "thinking"] as const) {
      const reference = part === "text" ? item.textRef : item.thinkingRef;
      if (!reference) continue;
      validateContentReference(reference);
      if (reference.threadId !== threadId || reference.itemId !== item.id || reference.part !== part ||
          reference.snapshotId !== snapshotId) {
        throw new Error("会话内容引用归属无效");
      }
      resolved[part] = await this.readContent(reference, current, budget);
    }
    return resolved;
  }

  private async resolveEventContent(event: HarnessEvent, current: () => void): Promise<{ text?: string; thinking?: string }> {
    const content: { text?: string; thinking?: string } = {};
    for (const part of ["text", "thinking"] as const) {
      const reference = part === "text" ? event.params?.textRef : event.params?.thinkingRef;
      if (!reference) continue;
      validateContentReference(reference);
      if (!event.params?.threadId || !event.params.itemId || reference.threadId !== event.params.threadId ||
          reference.itemId !== event.params.itemId || reference.part !== part || reference.snapshotId !== undefined) {
        throw new Error("会话事件内容引用归属无效");
      }
      const text = await this.readContent(reference, current);
      if (part === "text") content.text = text; else content.thinking = text;
    }
    return content;
  }
}
