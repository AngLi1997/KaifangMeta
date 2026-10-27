"""平台 · 认证模块：身份账号、全局唯一 sub、SSO 会话与 Token（OIDC 授权码 + PKCE）。

其他模块只通过 app.iam.service 的接口使用账号，不访问 iam schema 的表。
"""
