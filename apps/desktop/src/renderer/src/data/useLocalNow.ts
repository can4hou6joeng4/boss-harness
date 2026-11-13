import { useEffect, useReducer } from "react";

/** 只在需要显示时间的界面打开期间重绘；不依赖内核读取或事件。 */
export function useLocalNow(active = true): number {
  const [, refresh] = useReducer((tick: number) => tick + 1, 0);
  useEffect(() => {
    if (!active) return;
    const timer = window.setInterval(() => refresh(), 15_000);
    return () => window.clearInterval(timer);
  }, [active]);
  // 每次渲染都取当前时刻，页面重新打开或其他状态变化时也不会沿用上次节拍的时间。
  return Date.now();
}
