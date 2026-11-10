/**
 * 弹窗初始焦点的选择顺序。
 *
 * 单行输入优先（搜索、新建技能等沿用原有行为），其次多行文本域，最后才回退到
 * 弹窗里第一个可聚焦控件。文本域弹窗（编辑排队消息、编辑技能）此前被跳过，
 * 焦点只能落在标题栏的关闭按钮上：直接键入不进入正文，误按 Enter 还会关闭弹窗。
 */
export function pickFocusTarget<T extends { tagName: string }>(items: readonly T[]): T | undefined {
  return items.find(item => item.tagName === "INPUT")
    ?? items.find(item => item.tagName === "TEXTAREA")
    ?? items[0];
}
