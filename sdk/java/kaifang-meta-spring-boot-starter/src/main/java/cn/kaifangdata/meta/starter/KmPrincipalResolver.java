package cn.kaifangdata.meta.starter;

import org.springframework.security.core.Authentication;

/**
 * 业务扩展点：把已验签的平台身份转换为业务自己的认证对象（按 sub 关联本地用户、加载本地角色）。
 * 返回 null 表示不认证，由业务的认证入口返回 401。
 */
@FunctionalInterface
public interface KmPrincipalResolver {
    Authentication resolve(KmContext context);
}
