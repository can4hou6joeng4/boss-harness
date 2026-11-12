import { useRef, type KeyboardEvent } from "react";
import { ModalSurface } from "./ModalSurface";
import type { ThreadUsageBucket, ThreadUsageTurn } from "@boss-harness/protocol";
import type { MessageItem } from "../data/mockData";
import type { ThreadUsageState, UsageView } from "../data/useThreadUsage";
import { useClipboardCopy } from "../data/clipboardCopy";
import { buildUsageCsv, usageAmount, usageClip, usageJobSource, usageReasonEntries, usageUnreported, USAGE_JOB_REASONS } from "../data/usageReport";
import { USAGE_VIEWS, usageViewStep } from "../data/usageViewKeys";
import { compactionLabel, compactionTitle } from "../shell/queueCompaction";
import { turnTimingLabel } from "../data/turnTiming";
import "../styles/context-panel.css";

const DASH = "—";
const number = (value: number) => value.toLocaleString("zh-CN");
/** 没有可验证请求时整行显示“—”，避免把 0 当成 provider 上报的事实。 */
const amount = (bucket: ThreadUsageBucket, value: number | null) => {
  const known = usageAmount(bucket, value);
  return known === null ? DASH : number(known);
};
const reasons = (bucket: ThreadUsageBucket) => usageReasonEntries(bucket)
  .map(({ label, count }) => `${label} ${number(count)} 次`).join("、");

function Facts({ bucket, label }: { bucket: ThreadUsageBucket; label: string }) {
  return <div data-usage-bucket={label}>
    <dl className="context-panel-detail usage-facts">
      <dt>模型请求</dt><dd data-usage-field="requests">{number(bucket.requests)} 次{bucket.unverifiedRequests > 0 ? `（计入 ${number(bucket.verifiedRequests)} 次，不计入 ${number(bucket.unverifiedRequests)} 次）` : ""}</dd>
      <dt>输入 token</dt><dd data-usage-field="promptTokens">{amount(bucket, bucket.promptTokens)}</dd>
      <dt>其中未缓存</dt><dd data-usage-field="uncachedInputTokens">{amount(bucket, bucket.uncachedInputTokens)}</dd>
      <dt>缓存读取</dt><dd data-usage-field="cacheReadTokens">{amount(bucket, bucket.cacheReadTokens)}</dd>
      <dt>缓存写入</dt><dd data-usage-field="cacheWriteTokens">{amount(bucket, bucket.cacheWriteTokens)}</dd>
      <dt>输出 token</dt><dd data-usage-field="outputTokens">{amount(bucket, bucket.outputTokens)}</dd>
      <dt>其中推理</dt><dd data-usage-field="reasoningTokens">{amount(bucket, bucket.reasoningTokens)}</dd>
      <dt>费用</dt><dd data-usage-field="cost">未计价</dd>
    </dl>
    {usageUnreported(bucket) > 0 && <p className="context-panel-note" data-usage-field="unreportedRequests">provider 未上报用量 {number(usageUnreported(bucket))} 次：这些请求没有 token 数据，不按 0 计入。</p>}
    {bucket.unverifiedRequests > 0 && <p className="context-panel-note" data-usage-field="unverifiedReasons">未计入合计：{reasons(bucket)}。</p>}
  </div>;
}

/** 打开弹窗时固定的用量目标：系统通知切换活动会话不能改换统计对象。 */
export interface UsageTarget { threadId: string; title: string }
/**
 * 会话用量（只读）：本会话合计、摘要任务与每回合 provider 上报用量。
 * 数值逐项来自 thread/usage/read；provider 未上报的字段显示为“—”，不估算、不计价。
 */
export function UsageDialog({ isOpen, onClose, state, messages, target, branchViews, connected, onRefresh, onViewChange }: {
  isOpen: boolean; onClose: () => void; state: ThreadUsageState; messages: MessageItem[]; target: UsageTarget; branchViews: boolean; connected: boolean;
  onRefresh: () => void; onViewChange: (view: UsageView) => void;
}) {
  // 弹窗关闭时也要保持 hook 调用顺序一致，因此放在提前返回之前。
  const clipboard = useClipboardCopy();
  const viewGroup = useRef<HTMLDivElement>(null);
  if (!isOpen) return null;
  const data = state.data?.view === state.view ? state.data : undefined;
  const order = [...new Set(messages.flatMap(message => message.turnId ? [message.turnId] : []))];
  const inputOf = (turnId: string) => messages.find(message => message.role === "user" && message.turnId === turnId)?.content;
  const turnLabelById = (turnId: string) => { const index = order.indexOf(turnId); return index >= 0 ? `第 ${index + 1} 回合` : "不在当前视图"; };
  const turnLabel = (turn: ThreadUsageTurn) => turnLabelById(turn.turnId);
  // WAI-ARIA 单选组：方向键在范围内循环切换，焦点跟随新选中项。
  // 按住方向键不重复切换，否则每个重复事件都会重新发起一次 thread/usage/read。
  const moveView = (event: KeyboardEvent<HTMLDivElement>): void => {
    if (event.defaultPrevented || event.metaKey || event.ctrlKey || event.altKey) return;
    const next = usageViewStep(state.view, event.key);
    if (!next) return;
    event.preventDefault();
    if (event.repeat) return;
    if (next !== state.view) onViewChange(next);
    viewGroup.current?.querySelector<HTMLButtonElement>(`[data-usage-view="${next}"]`)?.focus();
  };
  return <ModalSurface title="会话用量" onClose={onClose} className="context-panel usage-dialog">
    <div className="context-panel-body">
      <div className="context-panel-owner" data-usage-owner={target.threadId}><strong>{target.title || "当前会话"}</strong><code>{target.threadId}</code></div>
      <p className="context-panel-note">用量目标在打开此窗口时确定；即使其他会话的通知切换了背景会话，这里仍显示上面这条会话的用量。</p>
      <p className="context-panel-source" data-usage-source>来源为 provider 上报的用量（按回合汇总已保存的记录，不做估算）；未上报的字段显示为“—”。费用未计价。</p>
      <div className="context-panel-section-heading usage-toolbar">
        {branchViews ? <div className="usage-view" role="radiogroup" aria-label="用量范围" ref={viewGroup} onKeyDown={moveView}>
          {USAGE_VIEWS.map(view => <button key={view} type="button" role="radio" aria-checked={state.view === view} data-usage-view={view}
            tabIndex={state.view === view ? 0 : -1}
            className={`secondary-button${state.view === view ? " active" : ""}`} onClick={() => onViewChange(view)}>{view === "log" ? "全部记录" : "当前分支"}</button>)}
        </div> : <span />}
        <div className="usage-actions">
          {clipboard.feedback?.key === "usage-csv" && <span role="status" className="usage-copy-feedback" data-usage-copy-feedback>
            {clipboard.feedback.ok ? "已复制" : `复制失败：${clipboard.feedback.reason}`}
          </span>}
          <button type="button" className="secondary-button" data-usage-copy disabled={!data}
            title={data ? "把当前视图已加载的用量复制为 CSV" : "当前视图的用量尚未加载"}
            onClick={() => { if (data) void clipboard.copy(buildUsageCsv(data, { turnLabel: turnLabelById, inputOf }), "usage-csv"); }}>复制 CSV</button>
          <button type="button" className="secondary-button" disabled={!connected || state.loading} onClick={onRefresh}>{state.loading ? "正在读取…" : "刷新"}</button>
        </div>
      </div>
      {!connected && <p className="context-panel-warning" role="status">本地内核未连接，暂不能读取用量。</p>}
      {state.error && <p className="context-panel-warning" role="alert">读取用量失败：{state.error}</p>}
      {data && <>
        <section className="context-panel-section" aria-label="本会话合计">
          <h3>本会话合计</h3>
          <Facts bucket={data.totals} label="totals" />
          {data.cacheWaste && <dl className="context-panel-detail usage-facts" data-usage-bucket="cacheWaste">
            <dt>缓存未命中</dt>
            <dd data-usage-field="cacheWaste">{number(data.cacheWaste.missedTokens)} token（{number(data.cacheWaste.missCount)} 次）</dd>
          </dl>}
          <p className="context-panel-note">合计包含业务回合与摘要任务；{state.view === "branch" ? "“当前分支”只统计当前分支上的回合，摘要任务不区分分支。" : "“全部记录”包含已切离分支上的回合。"}</p>
          {data.cacheWaste && <p className="context-panel-note">缓存未命中按相邻两次已验证请求估算：取两次输入 token 的较小值减去本次缓存读取，只累计超过 1024 token 的部分；压缩或分支摘要后重新建立基线。费用未计价。</p>}
          {!data.cacheWaste && state.view === "branch" && <p className="context-panel-note">缓存未命中只在“全部记录”视图统计；旧内核不返回该统计。</p>}
        </section>
        {data.summaryTasks.requests > 0 && <section className="context-panel-section" aria-label="摘要任务">
          <h3>摘要任务</h3>
          <Facts bucket={data.summaryTasks} label="summaryTasks" />
        </section>}
        {data.summaryJobs && data.summaryJobs.length > 0 && <section className="context-panel-section" aria-label="摘要任务明细">
          <h3>摘要任务明细<small className="usage-count"> {number(data.summaryJobCount ?? data.summaryJobs.length)} 个任务{data.summaryJobsTruncated ? `，仅显示最近 ${number(data.summaryJobs.length)} 个` : ""}</small></h3>
          <div className="usage-table-wrap"><table className="usage-table">
            <thead><tr><th>摘要任务</th><th>回合</th><th>模型</th><th>请求</th><th>输入</th><th>输出</th></tr></thead>
            <tbody>{data.summaryJobs.map(job => <tr key={job.jobId} data-usage-summary-job={job.jobId}>
              <td><span>{usageJobSource(job)}</span>{job.active && <span className="usage-active-badge" data-usage-field="active" title="当前分支上已验证生效的压缩摘要任务">当前生效</span>}<small title={job.jobId}>{[job.reason ? USAGE_JOB_REASONS[job.reason] ?? job.reason : "", job.origin === "user" ? "手动" : job.origin === "model" ? "自动" : ""].filter(Boolean).join(" · ") || job.jobId}</small></td>
              <td><span>{job.turnId ? turnLabelById(job.turnId) : DASH}</span>{job.throughTurnId && job.throughTurnId !== job.turnId && <small data-usage-field="throughTurnId">摘要至 {turnLabelById(job.throughTurnId)}</small>}</td>
              <td><span>{job.models.join("、") || DASH}</span><small>{job.providers.join("、")}</small></td>
              <td data-usage-field="requests">{number(job.requests)}{usageUnreported(job) > 0 && <small title="provider 未上报用量，不是 0">未上报 {number(usageUnreported(job))}</small>}{job.unverifiedRequests > usageUnreported(job) && <small title={`未计入：${reasons(job)}`}>不计入 {number(job.unverifiedRequests - usageUnreported(job))}</small>}</td>
              <td data-usage-field="promptTokens">{amount(job, job.promptTokens)}</td>
              <td data-usage-field="outputTokens">{amount(job, job.outputTokens)}</td>
            </tr>)}</tbody>
          </table></div>
          <p className="context-panel-note">明细按内核记录的任务编号汇总；没有任务编号的旧记录只计入上方合计。分支摘要的回合为切换前的目标回合，压缩摘要另标注记录中覆盖到的回合。“当前生效”来自当前分支上验证通过的压缩摘要，不由用量记录推断。</p>
        </section>}
        <section className="context-panel-section" aria-label="每回合用量">
          <h3>每回合用量<small className="usage-count"> {number(data.turnCount)} 个回合有记录{data.truncated ? `，仅显示前 ${number(data.turns.length)} 个` : ""}</small></h3>
          {data.turns.length ? <div className="usage-table-wrap"><table className="usage-table">
            <thead><tr><th>回合</th><th>模型</th><th>请求</th><th>输入</th><th>缓存读</th><th>缓存写</th><th>输出</th><th>推理</th></tr></thead>
            <tbody>{data.turns.map(turn => {
              const timing = turnTimingLabel(turn);
              return <tr key={turn.turnId} data-usage-turn={turn.turnId}>
              <td><span title={inputOf(turn.turnId)}>{turnLabel(turn)}</span><small>{usageClip(inputOf(turn.turnId), turn.turnId)}</small>
                {timing && <small data-usage-field="turnTiming">{timing}</small>}
                {turn.compactionPolicy && <small data-usage-field="compactionPolicy" title={compactionTitle(turn.compactionPolicy)}>{compactionLabel(turn.compactionPolicy)}</small>}
                {turn.skillIds && turn.skillIds.length > 0 && <small data-usage-field="skillIds" title={turn.skillIds.join("、")}>技能：{turn.skillIds.join("、")}</small>}
              </td>
              <td><span>{turn.models.join("、") || DASH}</span><small>{turn.providers.join("、")}</small></td>
              <td data-usage-field="requests">{number(turn.requests)}{usageUnreported(turn) > 0 && <small data-usage-unreported title="provider 未上报用量，不是 0">未上报 {number(usageUnreported(turn))}</small>}{turn.unverifiedRequests > usageUnreported(turn) && <small title={`未计入：${reasons(turn)}`}>不计入 {number(turn.unverifiedRequests - usageUnreported(turn))}</small>}</td>
              <td data-usage-field="promptTokens">{amount(turn, turn.promptTokens)}</td>
              <td data-usage-field="cacheReadTokens">{amount(turn, turn.cacheReadTokens)}</td>
              <td data-usage-field="cacheWriteTokens">{amount(turn, turn.cacheWriteTokens)}</td>
              <td data-usage-field="outputTokens">{amount(turn, turn.outputTokens)}</td>
              <td data-usage-field="reasoningTokens">{amount(turn, turn.reasoningTokens)}</td>
            </tr>; })}</tbody>
          </table></div> : <p className="context-panel-note">还没有模型用量记录。</p>}
          <p className="context-panel-note">“输入”含缓存读写（OpenAI 的输入本身已含缓存读取，Anthropic 由内核合并）；“推理”包含在“输出”内。不计入的记录不参与任何数值。回合下的压缩标记来自该回合开始时记录的自动压缩策略，悬停可看摘要线路。</p>
        </section>
      </>}
      {!data && state.loading && <p className="context-panel-note" role="status">正在读取用量…</p>}
    </div>
  </ModalSurface>;
}
