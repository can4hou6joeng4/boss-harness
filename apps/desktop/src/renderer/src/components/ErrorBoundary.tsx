import React from "react";
import { describeThrown, errorDetailText, errorSummary, type ErrorReport } from "../data/errorReport";
import "../styles/error-boundary.css";

interface ErrorBoundaryProps {
  children: React.ReactNode;
  /** 出错区域名称，用于摘要与复制详情，例如「会话区」。 */
  scope: string;
  /** 附加说明，告诉用户哪些东西仍然可用。 */
  hint?: string;
  /** 紧凑布局：嵌在版面内时减少留白。 */
  compact?: boolean;
}

interface ErrorBoundaryState {
  report: ErrorReport | null;
  componentStack: string;
  /** 递增后作为子树 key，强制重新挂载。 */
  attempt: number;
  copyNote: string;
  occurredAt: string;
}

/**
 * 渲染错误边界。
 *
 * 只在渲染阶段生效：事件处理器与异步回调里的异常不会经过这里。出错后
 * 冻结子树并显示可读摘要，用户可重试（重新挂载）、重新加载或复制详情。
 * 父组件可用 `key` 在切换会话等场景重置整个边界。
 */
export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  state: ErrorBoundaryState = { report: null, componentStack: "", attempt: 0, copyNote: "", occurredAt: "" };
  /** 复制详情是异步的；卸载后不再写状态。 */
  private mounted = false;
  /** 复制详情与错误状态共用的版本号；旧版本的回执不得更新界面。 */
  private copyVersion = 0;

  static getDerivedStateFromError(error: unknown): Partial<ErrorBoundaryState> {
    return { report: describeThrown(error), componentStack: "", copyNote: "", occurredAt: new Date().toISOString() };
  }

  componentDidMount(): void {
    this.mounted = true;
  }

  componentWillUnmount(): void {
    this.mounted = false;
  }

  componentDidCatch(error: unknown, info: React.ErrorInfo): void {
    // 新错误与上一份详情上的在途复制无关，旧回执不得出现在这张卡片上。
    this.copyVersion += 1;
    // 控制台保留原始对象，便于开发期排查；界面只显示收敛后的摘要。
    console.error(`[${this.props.scope}] 渲染异常`, error);
    if (info.componentStack) this.setState({ componentStack: info.componentStack });
  }

  private retry = (): void => {
    // 重试会丢弃当前错误卡片，此前发起的复制回执随之失效。
    this.copyVersion += 1;
    this.setState(state => ({
      report: null, componentStack: "", copyNote: "", occurredAt: "", attempt: state.attempt + 1,
    }));
  };

  private reload = (): void => {
    window.location.reload();
  };

  private copyDetail = async (): Promise<void> => {
    const { report, componentStack, occurredAt } = this.state;
    if (!report) return;
    // 只有最近一次复制可以写回执；开始新复制时先撤下旧提示。
    const version = ++this.copyVersion;
    const text = errorDetailText(report, { scope: this.props.scope, occurredAt, componentStack });
    this.setState({ copyNote: "" });
    try {
      if (!navigator.clipboard?.writeText) throw new Error("clipboard unavailable");
      await navigator.clipboard.writeText(text);
      if (this.mounted && version === this.copyVersion) this.setState({ copyNote: "已复制错误详情。" });
    } catch {
      if (this.mounted && version === this.copyVersion) this.setState({ copyNote: "复制失败：当前环境不允许写入剪贴板。" });
    }
  };

  render(): React.ReactNode {
    const { report, copyNote, attempt } = this.state;
    if (!report) {
      // attempt 变化时换 key，让「重试」真正重新挂载子树，而不是复用崩溃前的实例。
      return <React.Fragment key={attempt}>{this.props.children}</React.Fragment>;
    }
    const compact = this.props.compact === true;
    return (
      <div className={`error-boundary ${compact ? "error-boundary--compact" : ""}`} role="alert">
        <div className="error-boundary__card">
          <div className="error-boundary__title">界面出现异常</div>
          <div className="error-boundary__summary" style={{ userSelect: "text" }}>
            {errorSummary(report, this.props.scope)}
          </div>
          <div className="error-boundary__hint">
            {this.props.hint ?? "会话与内核仍在运行；重试会重新加载这块界面，不会删除本地会话。"}
          </div>
          <div className="error-boundary__actions">
            <button type="button" className="error-boundary__action error-boundary__action--primary" onClick={this.retry}>重试</button>
            <button type="button" className="error-boundary__action" onClick={this.reload}>重新加载</button>
            <button type="button" className="error-boundary__action" onClick={() => { void this.copyDetail(); }}>复制详情</button>
          </div>
          {copyNote && <div className="error-boundary__note" role="status">{copyNote}</div>}
        </div>
      </div>
    );
  }
}
