#!/usr/bin/env python3
"""核对审批提示音的偏好、间隔、上下文缓存与播放调度。

`approvalChime.ts` 只在偏好明确为 `"true"` 时开启提示音，存储读取异常按关闭处理；
播放要求时间可读且与上次播放满足最小间隔（默认 1500ms），`lastPlayedAt` 非法
视为从未播放；首个用户手势中预热音频上下文并恢复挂起状态；播放两声短提示音
（880 / 1318.51 Hz，间隔 0.13s），自动播放受限、上下文不可用或构造失败时静默
返回 false。这里用 Node 在临时目录加载真实模块并注入假 `window.AudioContext`
与假 `localStorage` 逐项核对。
"""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
CHIME = "apps/desktop/src/renderer/src/data/approvalChime.ts"
UI_STORAGE = "apps/desktop/src/renderer/src/data/uiStorage.ts"
DOCS = "docs/TECHNICAL_REFERENCE.md"

CHIME_FRAGMENTS = (
    'const SOUND_KEY = `${UI_STORAGE_PREFIX}approvalSound`;',
    "export const APPROVAL_SOUND_MIN_GAP_MS = 1500;",
    "let lastPlayedAt = 0;",
    "let audio: AudioContext | null = null;",
    "export function approvalSoundEnabled(",
    'read() === "true"',
    "export function approvalSoundDue(enabled: boolean, now: number, lastPlayed: number, gap = APPROVAL_SOUND_MIN_GAP_MS): boolean {",
    "if (!enabled || !Number.isFinite(now)) return false;",
    "if (!Number.isFinite(lastPlayed) || lastPlayed <= 0) return true;",
    "return now - lastPlayed >= gap;",
    "function audioContext(): AudioContext | null {",
    "if (audio) return audio;",
    'if (typeof window === "undefined" || typeof window.AudioContext !== "function") return null;',
    "audio = new window.AudioContext();",
    "export function primeApprovalChime(): void {",
    "const context = audioContext();",
    "export function playApprovalChime(now = Date.now()): boolean {",
    "if (!approvalSoundDue(true, now, lastPlayedAt)) return false;",
    "lastPlayedAt = now;",
    "for (const [index, frequency] of [880, 1318.51].entries()) {",
    'oscillator.type = "sine";',
    "oscillator.stop(at + 0.13);",
)

NODE_SCRIPT = r"""
import { pathToFileURL } from "node:url";
const url = pathToFileURL(process.argv[1]).href;
const created = [];
const oscillators = [];
let failConstruct = false;
let resumeRejects = false;
class FakeAudioContext {
  constructor() {
    if (failConstruct) throw new Error("no audio");
    this.state = "suspended";
    this.currentTime = 10;
    this.destination = { name: "out" };
    this.resumeCalls = 0;
    created.push(this);
  }
  resume() {
    this.resumeCalls += 1;
    return resumeRejects ? Promise.reject(new Error("blocked")) : Promise.resolve();
  }
  createOscillator() {
    const osc = {
      type: "",
      frequency: { values: [], setValueAtTime(value, at) { this.values.push([value, at]); } },
      target: null,
      gain: null,
      connect(target) { this.target = target; if (target && target.gain) this.gain = target; return target; },
      start(at) { this.started = at; },
      stop(at) { this.stopped = at; },
    };
    oscillators.push(osc);
    return osc;
  }
  createGain() {
    return {
      gain: {
        values: [],
        setValueAtTime(value, at) { this.values.push(["set", value, at]); },
        exponentialRampToValueAtTime(value, at) { this.values.push(["ramp", value, at]); },
      },
      target: null,
      connect(target) { this.target = target; return target; },
    };
  }
}
globalThis.window = { AudioContext: FakeAudioContext };
const base = await import(`${url}?case=base`);
const enabled = [
  [base.approvalSoundEnabled(() => "true"), base.approvalSoundEnabled(() => "false"),
    base.approvalSoundEnabled(() => "TRUE"), base.approvalSoundEnabled(() => null)],
  base.approvalSoundEnabled(() => { throw new Error("denied"); }),
  (() => {
    const defaults = [];
    defaults.push(base.approvalSoundEnabled());
    globalThis.localStorage = { getItem: () => "true" };
    defaults.push(base.approvalSoundEnabled());
    globalThis.localStorage = { getItem: () => { throw new Error("blocked"); } };
    defaults.push(base.approvalSoundEnabled());
    delete globalThis.localStorage;
    return defaults;
  })(),
];
const due = [
  [
    base.approvalSoundDue(false, 1000, 0),
    base.approvalSoundDue(true, Number.NaN, 0),
    base.approvalSoundDue(true, 1000, 0),
    base.approvalSoundDue(true, 3000, 2000),
    base.approvalSoundDue(true, 3499, 2000),
    base.approvalSoundDue(true, 3500, 2000),
  ],
  [
    base.approvalSoundDue(true, 1000, 950, 100),
    base.approvalSoundDue(true, 1000, 900, 100),
    base.approvalSoundDue(true, 1000, 900, 0),
  ],
  [
    base.approvalSoundDue(true, 1000, -5),
    base.approvalSoundDue(true, 1000, Number.NaN),
    base.approvalSoundDue(true, 1000, Number.POSITIVE_INFINITY),
  ],
];
created.length = 0;
const primeMod = await import(`${url}?case=prime`);
primeMod.primeApprovalChime();
primeMod.primeApprovalChime();
const prime = [created.length, created[0].resumeCalls, created[0].state];
created.length = 0;
oscillators.length = 0;
const playMod = await import(`${url}?case=play`);
const first = playMod.playApprovalChime(5000);
const schedule = oscillators.map(osc => [
  osc.frequency.values[0],
  Number(osc.started.toFixed(2)),
  Number(osc.stopped.toFixed(2)),
  osc.type,
  osc.gain.gain.values.map(([kind, value, at]) => [kind, value, Number(at.toFixed(2))]),
  osc.gain.target === created[0].destination,
  osc.target === osc.gain,
]);
const gap = [playMod.playApprovalChime(6000), playMod.playApprovalChime(6500)];
const resume = created[0].resumeCalls;
created.length = 0;
oscillators.length = 0;
failConstruct = true;
const throwMod = await import(`${url}?case=throw`);
const thrown = [throwMod.playApprovalChime(1000), throwMod.playApprovalChime(1100), throwMod.playApprovalChime(3000)];
failConstruct = false;
delete globalThis.window;
const noWindowMod = await import(`${url}?case=nowindow`);
const noWindowPlay = noWindowMod.playApprovalChime(1000);
let primeNoThrow = true;
try { noWindowMod.primeApprovalChime(); } catch { primeNoThrow = false; }
globalThis.window = { AudioContext: FakeAudioContext };
resumeRejects = true;
created.length = 0;
oscillators.length = 0;
const rejectMod = await import(`${url}?case=reject`);
const reject = [rejectMod.playApprovalChime(1000), created[0]?.resumeCalls ?? -1];
resumeRejects = false;
const results = {
  enabled,
  due,
  prime: [prime],
  play: [
    first,
    schedule,
    gap,
    resume,
    thrown,
    [noWindowPlay, primeNoThrow],
    reject,
  ],
};
process.stdout.write(JSON.stringify(results));
"""

EXPECTED_ENABLED = (
    [True, False, False, False],
    False,
    [False, True, False],
)
EXPECTED_DUE = (
    [False, False, True, False, False, True],
    [False, True, True],
    [True, True, True],
)
EXPECTED_PRIME = ([1, 2, "suspended"],)
SCHEDULE = [
    [[880, 10], 10, 10.13, "sine", [["set", 0.0001, 10], ["ramp", 0.06, 10.02], ["ramp", 0.0001, 10.12]], True, True],
    [[1318.51, 10.13], 10.13, 10.26, "sine", [["set", 0.0001, 10.13], ["ramp", 0.06, 10.15], ["ramp", 0.0001, 10.25]], True, True],
]
EXPECTED_PLAY = (
    True,
    SCHEDULE,
    [False, True],
    2,
    [False, False, False],
    [False, True],
    [True, 1],
)


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _expect(fragments: tuple[str, ...], text: str, label: str) -> int:
    missing = [fragment for fragment in fragments if fragment not in text]
    if missing:
        raise ValueError(f"{label} 缺少：" + "、".join(missing))
    return len(fragments)


def _node_matrix() -> dict:
    # approvalChime 以无扩展名相对路径导入 uiStorage；Node 的类型剥离只解析
    # 显式扩展名，所以复制到临时目录并改写导入，不改动仓库源文件。
    with tempfile.TemporaryDirectory() as directory:
        base = Path(directory)
        (base / "uiStorage.ts").write_text(_read(UI_STORAGE), encoding="utf-8")
        target = base / "approvalChime.ts"
        target.write_text(
            _read(CHIME).replace('from "./uiStorage"', 'from "./uiStorage.ts"'),
            encoding="utf-8",
        )
        try:
            result = subprocess.run(
                ["node", "--input-type=module", "--no-warnings", "-e", NODE_SCRIPT, str(target)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            raise ValueError("无法运行 node，请安装 Node.js 24+") from None
        except (OSError, subprocess.CalledProcessError) as error:
            detail = getattr(getattr(error, "stderr", None), "strip", lambda: "")()
            raise ValueError(
                "Node 审批提示音试算失败，请核对 Node.js 24+ 与 approvalChime.ts"
                + (f"：{detail[:200]}" if detail else "")
            ) from None
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        raise ValueError("Node 未返回有效的审批提示音结果") from None
    if not isinstance(payload, dict):
        raise ValueError("Node 未返回审批提示音矩阵")
    for key in ("enabled", "due", "prime", "play"):
        if not isinstance(payload.get(key), list):
            raise ValueError(f"Node 未返回 {key} 列表")
    return payload


def _compare(actual: list, expected: tuple, label: str) -> int:
    if len(actual) != len(expected):
        raise ValueError(f"审批提示音{label}用例数量变化：期望 {len(expected)}，实际 {len(actual)}")
    for index, (got, want) in enumerate(zip(actual, expected)):
        if got != want:
            raise ValueError(f"审批提示音{label}第 {index + 1} 个用例不符：期望 {want!r}，实际 {got!r}")
    return len(expected)


def _check_behaviors() -> int:
    payload = _node_matrix()
    checked = 0
    checked += _compare(payload["enabled"], EXPECTED_ENABLED, "偏好")
    checked += _compare(payload["due"], EXPECTED_DUE, "到期")
    checked += _compare(payload["prime"], EXPECTED_PRIME, "预热")
    checked += _compare(payload["play"], EXPECTED_PLAY, "播放")
    return checked


def _check_documentation() -> int:
    docs = _read(DOCS)
    if "`check_approval_chime.py`" not in docs:
        raise ValueError(f"{DOCS} 缺少 check_approval_chime.py")
    if "共 22 项结构、14 项行为" not in docs:
        raise ValueError(f"{DOCS} 需说明 check_approval_chime.py 检查 22 项结构、14 项行为")
    return 2


def check_approval_chime() -> tuple[int, int]:
    structure = _expect(CHIME_FRAGMENTS, _read(CHIME), CHIME)
    behavior = _check_behaviors()
    _check_documentation()
    return structure, behavior


def main() -> int:
    try:
        structure, behavior = check_approval_chime()
    except (OSError, ValueError) as error:
        print(f"审批提示音规则核对失败，{error}", file=sys.stderr)
        return 2
    print(f"审批提示音规则一致：{structure} 项结构、{behavior} 项行为")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
