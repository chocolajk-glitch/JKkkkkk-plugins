# EDY Codex Kit

2026-10-27 个人配置封装的公开分发版。插件名 `edy-workbench`，版本 `1.0.0`，marketplace 名 `edy-personal`。

## 包里有什么

- 14 个个人 Skills：codebase-design、diagnosing-bugs、domain-modeling、grill-me、grill-with-docs、grilling、improve-codebase-architecture、lark-context、setup-matt-pocock-skills、tdd、to-spec、to-tickets、wechat-context、reverse-engineer-anything。包含其脚本、参考文件及现有调用策略。
- 4 个 MCP 连接配置：GitHub、Tavily、OpenAI Docs、REA（固定 `rea-agents@6.7.0`）。工具由对应 MCP 提供，安装包不内置远程服务或 REA 分析引擎。
- 原有 Git 自动检查点 Hooks：UserPromptSubmit、Stop、Interrupt。安装并信任后可在任务结束时创建本地提交，不执行 push。Python 从 PATH 发现；状态默认放在插件的 `PLUGIN_DATA/git-checkpoints`，也可用 `CODEX_GIT_HOOK_STATE` 指定位置。
- `restore/`：模型/网关/桌面偏好的可选配置模板、原执行策略模板、上游插件恢复清单。安装插件不会自动应用这些模板。
- `inventory.json`：来源文件、源文件 SHA-256、兼容调整及未打包项目；`SHA256SUMS.json` 可验证交付文件是否变化。

这是 Windows 本地使用包。已移除个人用户名路径，模型网关替换为示例地址。飞书、微信的 D 盘启动器路径需要按本机环境调整。

## 下次怎么使用

1. 克隆本仓库或将整个目录解压到 D 盘一个固定位置。不要只复制 `plugins/`；marketplace 需要 `.agents/plugins/marketplace.json`。
2. 在该目录打开 PowerShell，先检查文件与环境：

   ```powershell
   python ./scripts/verify.py --environment
   ```

3. 在**新的 Codex 配置环境**注册并安装：

   ```powershell
   codex plugin marketplace add .
   codex plugin add edy-workbench@edy-personal
   ```

   也可以从 GitHub 直接注册本仓库：`codex plugin marketplace add chocolajk-glitch/JKkkkkk-plugins`。

   桌面端也可注册后重启，在 Plugins 的 `EDY Personal` 来源里安装。若客户端不识别，请升级到支持此 marketplace/插件格式的版本；本包已用本机 Codex CLI 0.164.0 测试。

4. 配置启动 Codex 的进程环境变量 `GITHUB_PAT_TOKEN`、`TAVILY_API_KEY`。`.env.example` 只列变量名，Codex 不会自动读取此文件。凭据缺失时，这两个 MCP 不能据此完成鉴权；其他 Skills 不需要这些凭据。
5. 重新启动会话。需要启用自动提交时，按客户端要求审阅并信任插件 Hooks。未信任的 Hooks 不会自动运行。

### 当前这台机器

本次只生成包并在隔离目录测试，**未改变你的全局配置，也未在当前环境启用插件**。你现在已有同名 Skills、4 个 MCP 及全局 Git Hooks；直接再安装会产生重复加载或重复检查点。

在当前机器切换前，先备份并将原个人 Skills 移出扫描目录，迁移对应的全局 MCP 条目，移除全局 Hooks 中相同的三个 `auto_commit.py` 调用，再安装插件。不要删掉桌面管理的 `node_repl`，也不要删除上游插件配置。切换完成后新开会话检查 Skills、`codex mcp list` 和 Hooks。包本身不自动实施这些迁移。

## 仍需单独准备的环境

| 能力 | 依赖 |
|---|---|
| Git 检查点 | PATH 中的 Python 3、Git；Git 作者信息；客户端信任 Hooks |
| REA MCP | Windows `cmd.exe`、Node.js/npm/npx；首次启动可能下载固定版本 npm 包；原生深度分析另需相应引擎 |
| 飞书 Skill | `D:/Tools/lark-cli/lark-cli.ps1`，与原配置分开保存的账号授权 |
| 微信 Skill | `D:/Tools/wechat-cli-local/wechat-cli.cmd`，本机微信及单独初始化的只读 CLI 数据环境 |
| 文档/表格/浏览器等上游插件 | 从原来源安装；见 `restore/upstream-plugins.json` |

飞书、微信 Skill 保留了当前 D 盘启动器路径；迁移到不同路径时更新对应 Skill。包不包含 CLI 的账号、微信密钥、数据库或聊天记录。

上游内置插件由目标桌面应用供应，Postman 使用原 `postmanlabs/postman-plugin` 来源。`openviking-memory@openviking` 的快照状态仍为 disabled；不因恢复清单而启用。

## 配置与能力边界

插件不能替代整份 Codex 用户配置。模型提供商、界面、全局记忆开关等保存在 `restore/config.example.toml`，如有需要手动合并。其中网关地址为占位示例，需要填写自己的服务地址并确认模型可用。原 `danger-full-access` 等执行设置放在单独的 `execution-policy.example.toml` 中，不自动应用。

未打包桌面内部的 `node_repl`、通知程序、运行时目录、会话管道 ID、上游插件缓存、系统 Skills、登录凭据、聊天记忆、自动化、项目信任记录或 Hook 信任哈希。目标桌面应自行供应内部工具。

采用官方仍支持的 `.codex-plugin/plugin.json` + `.mcp.json` 兼容布局，以匹配当前客户端。六个旧 Skill 的 `disable-model-invocation` 字段已移除，现有 `agents/openai.yaml` 的显式调用策略保留；若干 `Skill tool` 指令改为读取包内对应 Skill，其业务流程未重写。详见 inventory。

## 验证证据

见 `VALIDATION.md`。安装识别和 MCP 配置识别不代表每个远程服务已完成调用；本次未重新验证 GitHub/Tavily 账号、飞书/微信内容访问或 REA 原生引擎。

官方格式与分发参考：[Package your plugin](https://developers.openai.com/plugins/build/plugins)。
