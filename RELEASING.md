# 版本交付与项目介绍

本文约定如何把已合并的改进交付为可追溯版本，并同步使用说明与社区介绍。提交、PR、验证材料和招聘操作边界仍以 [CONTRIBUTING.md](CONTRIBUTING.md) 为准。

## 何时准备版本

候选期满足下列任一条件时，先做版本与文档汇总，再继续下一批能力或缺陷选题：

- 自上次发布起累计至少 5 个影响使用者的 PR。
- 距上次发布满 7 天，且有新的已合并变化。
- 主要能力、兼容边界或安装方式发生变化，或用户要求交付版本。

这是准备候选版本的触发条件；实际发布仍需要对应授权。一次聚合版本可以包含多项修复，不为每个小修复单独增加候选号。没有新变化时不空发版，构建或验收失败时记录阻碍与下一步，不标为已发布。

## 版本与文档一起准备

1. 从最新 `origin/main` 列出上次实际发布 tag 之后的提交与关联 PR，区分能力、修复、兼容变化和文档。以远程 tag / Release 为依据，不能只看主干中的版本字符串。
2. 建立发布 Issue，记录拟发布版本、基线、包含范围、验收、产物与未完成事项；已有待处理 release PR 时先核对其基线和变更范围，不直接沿用过期分支。
3. 按 SemVer 判断兼容影响。候选版本的 npm 拼写形如 `0.2.0-rc.N`，Python 使用对应的 PEP 440 拼写 `0.2.0rcN`；序号不设位数上限（`0.2.0-rc.101` 与 `0.2.0rc101` 同样有效）。桌面版本展示按不透明字符串处理；Python 发布脚本用 `packaging.version.Version` 解析并按 PEP 440 归一写入清单，因此 `--version` 应使用 `pyproject.toml` 的 Python 拼写。JSON-RPC 协议版本独立管理，不随候选号机械改变。
4. 在独立 release 分支同步根包、桌面包、各工作区包、锁文件与 Python 包的版本来源。用 Node.js 24+ 和 Python 3.11+ 运行 `python scripts/check_versions.py`，核对 npm 实际发现的工作区、锁文件、`pyproject.toml`、内核 `__version__`、`CHANGELOG.md` 首条版本与使用指南的源码版本行。协议方法、通知或能力有变化时，再运行 `python scripts/check_protocol.py` 核对 `ClientMethods`、`ServerNotifications`（含宿主通知与动态发送登记）、`ServerRequests`、`InitializeResponse.capabilities`、桌面方法字面量以及 `RENDERER_METHODS` / `THREAD_METHODS` 白名单。搜索归一化的映射表、Node 运行时或最低 Python 版本有变化时，运行 `python scripts/check_search_unicode.py` 对照全部 Unicode 码点；CI 在 Python 3.10–3.14 上分别执行该检查并编译内核与脚本源码。移动或新增用户文档后，运行 `python scripts/check_docs_links.py` 核对相对链接、页内锚点与 docs 索引。脚本成功时输出 Python 版本，Source build 复用该结果生成资产清单和核对隔离安装。运行时和关于页的版本展示另行核对。
5. 把待发布内容从 CHANGELOG 的「未发布」整理为具名版本，保留链接、兼容影响与验证限制；未被本次版本包含的内容留在「未发布」。
6. 同步 README 的简短版本状态、首次启动步骤与文档入口：首页只保留当前源码/发布关系的稳定事实，不追加批次修复清单或候选自检细节。首页写用户得到的行为，完整问题历史保留在 CHANGELOG、GitHub Release 与关联 PR。
7. 准备 Release 正文：定位、重点变化、升级方式、交付资产、来源、验证与限制。尚未执行的检查写为待执行，不能预先宣称通过。

版本文件清单应从当前源码核实；新增组件或动态版本来源后同步更新本次发布清单。不要把协议常量、上游 CLI 版本和历史 CHANGELOG 中的旧版本一起替换。

## 构建与验收

发布从指定提交的已跟踪内容构建。工作树里即使存在未跟踪图标、临时探针或本地配置，也不得随资产分发；先清理并重建输出目录，再把指定提交用 `git archive` 展开到新的临时目录，作为唯一的源码输入。以下命令应在同一个 shell 会话中执行，`SOURCE_DIR` 与 `COMMIT` 会被后续步骤复用：

```sh
set -euo pipefail
COMMIT="$(git rev-parse HEAD)"
git rev-parse --verify "$COMMIT^{commit}" >/dev/null
SOURCE_DIR="$(mktemp -d "${TMPDIR:-/tmp}/boss-harness-release.XXXXXX")"
git archive "$COMMIT" | tar -x -C "$SOURCE_DIR"
test -f "$SOURCE_DIR/package.json"
test -f "$SOURCE_DIR/harness/pyproject.toml"
cd "$SOURCE_DIR"
```

归档目录没有 `.git`，因此先在原始仓库确认提交可解析，再展开归档；后续脚本在该目录中只校验提交格式，不能再次证明提交存在。

桌面源码检查与构建：

```sh
cd "$SOURCE_DIR"
npm ci
npm run typecheck
npm run build
```

Python 内核包构建使用满足项目要求的独立环境。生成资产清单前先清空 `dist/python` 并重新构建，避免旧候选资产混入清单：

```sh
cd "$SOURCE_DIR"
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python build packaging
rm -rf dist/python
.venv/bin/python -m build ./harness --outdir dist/python
```

`git archive` 只包含提交中的已跟踪文件；不要直接从普通工作树构建发布资产，也不要给构建后端传入额外文件或目录。Source build 在 wheel / sdist 之后运行 `scripts/release_assets.py`，生成 `build-info.json` 与 `SHA256SUMS.txt`，并把整个目录作为 `python-dist` 工作流产物上传。本地复现使用同一入口，`--commit "$COMMIT"` 必须是构建输入的完整提交；在包含 `.git` 的 Git 仓库中脚本会用 `git rev-parse --verify` 确认该提交可解析，隔离归档目录则只校验格式。需要标明触发来源时传 `--source-ref`（例如 CI 的 `$GITHUB_REF`），否则清单不包含该字段：

```sh
cd "$SOURCE_DIR"
SOURCE_VERSION="$(.venv/bin/python scripts/check_versions.py)"
.venv/bin/python scripts/release_assets.py \
  --version "$SOURCE_VERSION" \
  --commit "$COMMIT" \
  --source-ref "refs/heads/main" \
  --out-dir dist/python \
  dist/python/*.whl dist/python/*.tar.gz
```

需要固定构建时间以便复核时，追加 `--built-at 2026-11-16T04:30:00Z`。脚本只处理输出目录内显式列出的普通文件，拒绝符号链接、目录、重复文件名与保留输出名；保留名和重复名按大小写不敏感比较。包名与版本按 `pyproject.toml` 和 PEP 440 归一后，与 wheel / sdist 文件名、sdist 根目录、wheel `METADATA`、sdist `PKG-INFO` 及 sdist 根 `pyproject.toml` 逐一核对，源 `harness/pyproject.toml` 的版本也必须与 `--version` 一致，不一致即失败。摘要按块流式计算，两个清单先写临时文件再原子替换。`build-info.json` 的 `schemaVersion` 为 `2`，记录项目名、Python 版本、源码提交（仓库内运行时仅接受可解析提交）、可选的 `sourceRef`、`builtAt`、构建用 Python 版本与每个资产的 `name` / `bytes` / `sha256`；`sourceRef` 只描述触发来源，不能替代提交。CI 的 `pull_request` 构建把临时 merge commit 记为 `sourceCommit`，同时用 `sourceRef: refs/pull/N/merge` 标明其可复现范围；该类产物不能当作已合并的稳定发布输入，实际发布须从最终 tag 提交重新构建。已发布 rc.15 的 `schemaVersion: 1` 使用 `release`、`source`（含 `commit` / `tree`）、`versions`（npm / python / protocol）、`build`、`assets[]`（`name` / `size` / `sha256`）、`license`、`verification`，两者结构不同，解析时必须按 schemaVersion 分流。`SHA256SUMS.txt` 覆盖 wheel、sdist 与最终 `build-info.json` 的摘要，不包含自身；生成后应执行 `sha256sum -c SHA256SUMS.txt`（macOS 可用 `shasum -a 256 -c SHA256SUMS.txt`）复核。工作流产物用于审阅与核对，不等于 GitHub Release 资产；实际发布仍须从 tag 提交重新构建、复核哈希后上传。

按本次变更补充适用的真实 Electron 离线验收；使用临时 HOME、userData、工作区与内核目录，隔离凭据和真实会话。`none` 仅表示不调用模型，部分命令仍可调用招聘 CLI，不能把它当成平台网络隔离；验收应独立阻断并核对模型、真实回合、招聘工具与平台网络尝试。

逐项记录验证来源与范围：

| 验证项 | 可以说明什么 |
| --- | --- |
| TypeScript 检查与 Electron 构建 | 生产 main / preload / renderer 可构建；不能证明桌面操作已验收。 |
| 真实 Electron 离线交互 | 实际窗口、生产桥接与本地交互按记录通过；不能证明真实模型或招聘平台可用。 |
| wheel / sdist 构建和隔离安装 | 内核包的内容、元数据与命令入口按记录可用；不能证明已有独立桌面安装包。 |
| 最新提交的远程 CI | GitHub 上该提交实际执行的源码构建与审计；本地未入库探针不能计为 CI 覆盖。 |
| 真实模型 / 平台 / 签名安装包 | 只在取得对应授权并实际完成后记录；未执行时明确列为未验收。 |

检查 wheel、sdist 与其他拟上传资产的文件列表和元数据，排除测试材料、离线替身、临时配置、凭据、本地状态和个人资料；记录文件大小与 SHA-256。若拟发布到包注册表，还需单独确认分发目标、许可证、包名与隔离安装结果。

## 合并与发布

release PR 的最新 head 必须通过全部约定检查。核对审查意见、源码与资产来源后，按完整 40 位 head SHA 绑定 squash 合并；不得管理员绕过、force push 或替换已发布历史。

发布前将具体的版本、合并提交、Release 正文、资产清单与哈希作为可审阅结果，并确认本次授权覆盖哪些动作：

- 推送 annotated tag。
- 创建 GitHub Release，并标为候选预发布。
- 上传已核对的资产。
- 向 npm、PyPI 等注册表发布（当前未实际发布，仅作为需单独授权的可选渠道）。

已有相应持续授权时按其范围执行；没有覆盖的动作在准备完成后统一确认。源码 PR 的推送 / 合并授权，不自动覆盖 tag、Release、注册表或第三方社区发送。当前实际发布资产以 [GitHub Releases](https://github.com/can4hou6joeng4/boss-harness/releases) 为准；不要把 wheel、sdist 构建产物或候选版本说明写成已发布到包注册表。

使用明确的合并提交创建 annotated tag，推送后核对 tag 指向。GitHub Release 使用已存在的 tag，不依赖工具自动创建轻量 tag；候选版本标为 prerelease。发布完成后再次读取远程 Release，核对 tag、提交、正文、资产名与哈希。连接中断或结果未知时先核对远端实际状态，不重复创建或覆盖。

记录实际 Release 链接，并同步 README 的已发布版本状态；候选修复清单和验证细节留在 CHANGELOG 与 Release 正文。未提供独立安装包时保留源码启动说明；不能用 Electron 的 `out/` 目录宣称已经支持独立安装。发布新版本不等于更改仓库可见性或选定开源许可证。

## 对外介绍

每次准备候选版本时同时准备短介绍，内容优先包含：

- 项目解决的具体问题，以及 Electron 工作台、Python Harness 和招聘 CLI 的职责边界。
- 可核实的当前版本、源码与 Release 链接、安装范围和许可证状态。
- 本项目自身的能力与接入方式；社区正文不表达参考或沿用其他仓库的关系，内部来源与许可证记录保留在 [UPSTREAM.md](UPSTREAM.md)。
- 验证范围和一个具体的反馈请求，例如会话恢复、审批边界或集成方式；避免只请求 star。

先阅读目标仓库的贡献与社区规则。优先选择其明确提供的 showcase、项目展示、集成讨论或相关应用入口；没有合适入口时先记录候选渠道，不在普通 bug Issue 中投放宣传。不得暗示官方合作或维护者背书，不重复发帖或批量联系。

发送前展示具体目标 URL、标题与正文；已有明确授权时按授权范围执行，没有时统一确认。草稿只能称为草稿，发送后才记录实际链接。对方明确拒绝、关闭不相关内容或要求转移渠道时遵从其规则。

对外只分享可公开的项目资料。模型凭据、招聘记录、个人资料、本机路径与私有配置不进入截图、示例、Issue、Discussion 或发布资产。按 [LICENSE](LICENSE) 说明源码采用 MIT；将项目向其他仓库介绍，不代表对方许可代码已被采用。
