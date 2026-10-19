# EasyEDA 插件协作规范

组织级唯一规范：[Partme Agent Plugin Architecture Rules v1](https://github.com/full-aigc-plugins/.github/blob/main/docs/standards/partme-agent-plugin-architecture-rules-v1.md)。

- 默认直接使用 Skills + 客户端原生 MCP；不复制 Agent Runtime、EDA 编辑引擎或任务数据库。
- skills/ 是独立 easyeda-skills 包的自包含快照。领域内容先在源包修改，再用 scripts/sync_skills.py 同步；快照不得依赖兄弟目录。
- displayName 必须是 EasyEDA；内置 MCP 与 Run API Gateway 是两条不同路径。
- 不以源码/静态检查代替实际设计与制造验证。只读任务不调用工程写入 API。
- CI 使用组织共享架构检查，不复制该实现。新高级 easyeda-mcp 单独维护实际领域接口。
