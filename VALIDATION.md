# 验证记录

日期：2026-10-27（Asia/Shanghai）。客户端：Codex CLI 0.164.0，Windows。

| 验证项 | 结果与范围 |
|---|---|
| 官方 Skill 校验器 | 14/14 通过 `skill-creator/scripts/quick_validate.py`；PyYAML 仅装入工作区的临时验证依赖目录 |
| 显式调用策略 | 原有 6 个 explicit-only Skills 的 `allow_implicit_invocation: false` 均保留 |
| 插件安装 | 隔离 `CODEX_HOME` 中 marketplace 注册与 `codex plugin add edy-workbench@edy-personal` 成功；插件列表显示 1.0.0、installed、enabled |
| MCP 配置 | 隔离环境 `codex mcp list --json` 识别 GitHub、Tavily、OpenAI Docs、REA；Bearer 环境变量名、REA 命令和 30/450 秒超时正确保留 |
| Git Hook 行为 | 临时 Git 仓库中的真实代码修改创建了本地提交，提交内容正确，索引恢复干净；重复 Stop 不重复提交；只读请求不创建 baseline |
| 原文件 | 所有源 Skill 文件的 SHA-256 与打包前一致，仅对交付副本做兼容调整 |
| 凭据 | 包中不包含账号配置、OAuth 存储、微信密钥或凭据文件；另检查当前进程能读取的两个配置凭据变量的字面值未被写入包，未输出变量值 |
| 完整性 | `scripts/verify.py` 检查 JSON/TOML、manifest 路径、Skill 入口与 SHA-256 文件清单；压缩后解压复核 |

结构化 Skill 与 Hook 验证结果见 `validation-details.json`。

本次未执行模型推理、远程 MCP 工具调用、GitHub/Tavily 登录、飞书/微信数据读取或 REA 原生引擎分析。MCP 配置识别不能证明这些服务的端到端可用性。Hooks 测试发生在临时仓库，未在全局配置中启用本插件，也未复制现有 Hook 信任状态。

Git Hook 仍保留原实现的行为：在符合条件的目录内可能初始化 Git，并为代码变更创建本地提交；启用前应阅读 `plugins/edy-workbench/scripts/auto_commit.py`。本次迁移仅修改其默认状态目录，不改变提交规则。
