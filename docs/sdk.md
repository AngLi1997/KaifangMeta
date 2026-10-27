# SDK / Starter 分发

| 包 | 包名 | 分发渠道 |
|----|------|----------|
| Python SDK | `kaifang-meta-sdk` | PyPI 私服 |
| Java Starter | `kaifang-meta-spring-boot-starter` | Maven 私服 |
| 前端壳 | `kaifang-meta-shell` | npm 私服 |

均使用语义化版本。

- **协议**：OIDC / JWT（JWKS 验签）、服务间认证（client credentials 换服务 Token）、REST（OpenAPI 定义并生成客户端）、事件（CloudEvents）、算子协议。
- **功能**：身份上下文、身份目录、服务间认证、能力调用（同步 / 异步回调）、事件订阅、[统一权限组件](platform/auth/authz.md)（RBAC，后端组件 + 前端壳内权限管理页面）、审计日志。
- 业务前端复用前端壳，仅替换主色与业务路由。
- 接入示例见 [应用接入](platform/auth/app-onboarding.md)。
