# boss-harness

BOSS Harness 的 Python 内核，以 stdio JSON-RPC `0.2.0` 服务端形式运行：负责执行循环、上下文预算与压缩、会话持久化与恢复、审批与停止，以及受限工作区技能加载。

- 不监听端口：只通过标准输入输出与桌面外壳通信，外壳不 import 内核代码。
- 招聘动作只经 `boss-agent-cli` 子进程完成；默认 14 个工具中 13 个只读，`boss_hr_greet` 需要逐次批准。
- 模型线路支持 OpenAI Responses、Anthropic Messages 与 `none`。`none` 走不调用模型的确定性回合，仍可调用招聘 CLI，不等于离线。

从主仓库源码安装（尚未发布到 PyPI）：

```bash
git clone https://github.com/can4hou6joeng4/boss-harness.git
cd boss-harness
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ./harness
.venv/bin/boss-harness --check --provider none
```

桌面外壳、协议包与完整使用说明在主仓库：<https://github.com/can4hou6joeng4/boss-harness>

变更记录见 [CHANGELOG](https://github.com/can4hou6joeng4/boss-harness/blob/main/CHANGELOG.md)。

MIT 许可。
