package cn.kaifangdata.meta.starter;

import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * 业务系统接入配置，值来自平台「应用接入」登记（client_id、密钥、网关前缀）。
 *
 * @param enabled       是否启用平台身份
 * @param issuer        认证模块地址，如 http://gw.internal:9080/kaifang-meta/iam
 * @param clientId      应用 client_id
 * @param clientSecret  应用密钥，用于换取 Service Token 调用身份目录
 * @param gatewaySecret 网关签名身份头的 HMAC 密钥
 * @param gatewayPrefix 应用在网关的前缀，如 /kaifang-meta/ub；网关在去前缀之前签名，验签时补回
 * @param signWindowMs  签名时间窗，默认 ±5 分钟
 * @param tenantId      单租户部署时后台任务（无请求身份）调用身份目录使用的租户
 */
@ConfigurationProperties("kaifang-meta")
public record KmProperties(boolean enabled, String issuer, String clientId, String clientSecret,
        String gatewaySecret, String gatewayPrefix, Long signWindowMs, String tenantId) {

    public long signWindow() {
        return signWindowMs == null ? 300_000 : signWindowMs;
    }

    /** 平台 API 与认证模块同一网关：…/kaifang-meta/iam → …/kaifang-meta/platform/iam/v1 */
    public String directoryUrl() {
        return issuer.replaceFirst("/kaifang-meta/iam/?$", "") + "/kaifang-meta/platform/iam/v1";
    }

    void validate() {
        if (blank(issuer) || blank(clientId) || blank(gatewaySecret) || gatewaySecret.startsWith("change-me")) {
            throw new IllegalStateException("kaifang-meta.issuer、client-id、gateway-secret 必须配置为平台登记的值");
        }
    }

    private static boolean blank(String value) {
        return value == null || value.isBlank();
    }
}
