# 让编码 Agent 协助完成本地安装

把这份文件交给你的编码 Agent，或直接对它说「按 SETUP.md 帮我安装并自检 BOSS Harness」。指南只覆盖从源码安装与离线自检；模型凭据、招聘平台登录与任何平台写操作始终由你本人完成。

> English: hand this file to a coding agent and ask it to follow the steps below. It installs from source and stops before credentials, model configuration and platform login. Commands are language-neutral; authoritative details live in [README.md](README.md) and [docs/USER_GUIDE.md](docs/USER_GUIDE.md).

## 给 Agent 的约定

- 一次只问一个问题；执行每条命令前先用一句话说明它会做什么、是否联网，得到用户确认后再运行。
- 不读取、不回显、不写入任何凭据。模型密钥与平台登录只由用户在自己的 shell 或桌面界面完成；发现凭据出现在配置、日志或工作树中时立即停止并提醒用户。
- 不执行招聘平台写操作，不打开真实浏览器登录，不调用真实模型做试探。本指南只用 `BOSS_HARNESS_PROVIDER=none` 与本地自检。
- 安装在仓库内创建 `.venv`、`node_modules` 与构建产物，首次验证在临时目录使用独立的内核状态。不修改用户的 shell 配置，不提交、不推送任何改动。
- 失败时先运行自检并按固定检查码排查；不要用重装或放宽目录权限来「绕过」自检。

## 1. 核对工具链

```sh
node --version      # 需要 24 或更高
python3 --version   # 需要 3.10 或更高；读取 Codex TOML 与开发建议 3.12
uv --version        # 缺失时让用户按官方说明安装
```

三项都满足后再继续。`python3` 过旧时，用 `uv python install 3.12` 提供的解释器创建虚拟环境；桌面最低要求 macOS 12。

## 2. 安装内核与桌面依赖

在仓库根目录依次运行：

```sh
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -e ./harness
npm ci
npx install-electron --no
```

`npx install-electron --no` 会联网下载并校验 Electron 运行时；失败时按[本地验证与构建](CONTRIBUTING.md#本地验证与构建)的说明重试，不要跳过这一步。

## 3. 运行本地配置自检

```sh
trial_dir="$(mktemp -d "${TMPDIR:-/tmp}/boss-harness-first-run.XXXXXX")"
BOSS_HARNESS_DIR="$trial_dir/state" .venv/bin/boss-harness --check --provider none --format text
```

保留这个终端，在第 4 步复用同一个 `trial_dir`。自检显式选择 `none`，并检查桌面将使用的临时内核状态路径。自检不创建该状态目录，不调用模型、执行招聘 CLI 或访问招聘平台。`通过` 或 `通过，N 项警告` 可以继续。若报告发现错误，先按检查码处理，再用同一路径重试。

| 检查结果 | 让用户做什么 |
| --- | --- |
| `MODEL_DISABLED` | 预期结果：本次显式禁用模型。其余检查没有错误即可继续第 4 步。 |
| `BOSS_CLI_UNAVAILABLE` | 未找到招聘 CLI 的警告，不影响验证桌面连接。准备使用招聘工具时再按[上游 CLI 设置](docs/USER_GUIDE.md#上游-cli-设置)安装并核对路径。 |
| `BOSS_CLI_DATA_DIR_IN_REPO` | 让用户把 `BOSS_CLI_DATA_DIR` 移到仓库外；登录态与平台缓存不应进入可能被提交的目录。这是警告，不阻止启动。 |
| `BOSS_CLI_DATA_DIR_OVERLAP` | 让用户为业务 CLI 数据目录与内核状态目录选择互不包含的两个目录。这是警告，不阻止启动。 |
| `STATE_DIRECTORY_*` | 按报告建议选择当前用户拥有的独立目录，不要放宽权限。 |
| `STATE_DIRECTORY_IN_REPO` | 让用户把状态目录移到仓库外；会话记录与附件不应进入可能被提交的目录。这是警告，不阻止启动。 |
| `STATE_DIRECTORY_LOW_SPACE` | 提醒用户释放磁盘空间；这是警告，不阻止启动。 |

完整检查码与处理建议见[本地配置自检](docs/USER_GUIDE.md#本地配置自检)。

## 4. 先用禁用模型的桌面验证链路

先退出已运行的桌面实例，再在第 3 步的终端启动，让新的进程读取本次配置。

```sh
BOSS_HARNESS_DIR="$trial_dir/state" BOSS_HARNESS_PROVIDER=none npm run dev
```

桌面显示已连接本地 Harness，即完成安装验证。临时目录存放本次验证的内核会话和附件，Electron 窗口设置由桌面应用管理。`none` 只禁用模型，招聘 CLI 仍可运行，验证到连接成功为止。

## 5. 交给用户：模型线路与平台登录

停止自动操作，让用户自己完成：

1. 按[模型配置来源](docs/USER_GUIDE.md#模型配置来源)在自己的 shell 设置 `ANTHROPIC_*` 或 `BOSS_HARNESS_OPENAI_*`；不要把密钥写进仓库、文档或日志。
2. 先关闭第 4 步的桌面进程。后续使用平时的内核状态路径时，在自检和启动命令中省略临时的 `BOSS_HARNESS_DIR="$trial_dir/state"`。自检用 `--provider` 指定目标线路（例如 `--provider openai`），通过后用同一线路的 `BOSS_HARNESS_PROVIDER` 启动桌面。
3. 需要招聘工具时，先安装并配置 `boss-agent-cli`，再由用户完成平台登录与浏览器来源配置；登录、验证码与风控步骤不要代劳。

## 6. 收尾

```sh
git status --short
```

确认没有 `.env`、日志、真实会话或凭据进入工作树；`.venv`、`node_modules` 与构建产物应被忽略。最后带用户回到 [README.md](README.md) 的「试跑一条任务」，从只读命令开始。
