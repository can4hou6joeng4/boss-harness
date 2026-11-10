/**
 * 在途请求的作废标记。
 *
 * 弹窗在等待异步结果期间可以被关闭、重新打开，甚至发起新的请求；旧请求返回时
 * 不能把提示、输入正文或忙碌态写回当前的界面。每次提交领取一个递增标记，
 * 关闭弹窗时作废全部未完成标记，异步回调只在与当前标记一致时才写回状态。
 */
export type AttemptToken = { current: number };

export function createAttemptToken(): AttemptToken {
  return { current: 0 };
}

/** 开始一次新提交：返回本次标记，同时作废之前所有未完成的提交。 */
export function startAttempt(tracker: AttemptToken): number {
  tracker.current += 1;
  return tracker.current;
}

/** 关闭弹窗等场景：作废全部未完成的提交。 */
export function invalidateAttempts(tracker: AttemptToken): void {
  tracker.current += 1;
}

export function attemptCurrent(tracker: AttemptToken, token: number): boolean {
  return token === tracker.current;
}
