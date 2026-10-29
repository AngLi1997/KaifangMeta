package cn.kaifangdata.meta.starter;

import jakarta.servlet.http.HttpServletRequest;

/**
 * 当前请求的平台身份，只在请求内有效；角色、菜单、权限由业务系统自行维护，不从身份头推导。
 *
 * @param sub           全局唯一用户 ID（服务调用时为调用方 client_id）
 * @param tenantId      租户
 * @param clientId      调用方应用
 * @param principalType user 或 service
 * @param requestId     网关请求 ID
 * @param onBehalfOf    代表用户的 sub（仅平台 API 使用）
 */
public record KmContext(String sub, String tenantId, String clientId, String principalType, String requestId,
        String onBehalfOf) {

    static final String ATTRIBUTE = KmContext.class.getName();

    public boolean isUser() {
        return "user".equals(principalType);
    }

    /** 当前请求的平台身份；请求未经平台网关时返回 null */
    public static KmContext of(HttpServletRequest request) {
        return (KmContext) request.getAttribute(ATTRIBUTE);
    }
}
