# kaifang-meta-spring-boot-starter

业务系统（Spring Boot 3）接入 KaifangMeta 平台：校验网关签名身份头、提供请求身份上下文、调用身份目录（账号与机构）。协议与边界见 [SDK](../../../docs/sdk.md)、[统建系统接入](../../../docs/platform/auth/onboarding-unified-build.md)。

## 构建

```bash
mvn -f sdk/java/kaifang-meta-spring-boot-starter/pom.xml install
```

## 引入

```xml
<dependency>
    <groupId>cn.kaifangdata.meta</groupId>
    <artifactId>kaifang-meta-spring-boot-starter</artifactId>
    <version>0.1.0-SNAPSHOT</version>
</dependency>
```

```yaml
kaifang-meta:
  enabled: true
  issuer: http://gw.internal:9080/kaifang-meta/iam
  client-id: kaifang-meta-unified-build
  client-secret: ${KM_CLIENT_SECRET}
  gateway-secret: ${KM_GATEWAY_SECRET}
  gateway-prefix: /kaifang-meta/ub     # 平台「应用接入」登记的网关前缀
  tenant-id: t_system                  # 后台任务调用身份目录时使用的租户
```

## 使用

1. 提供 `KmPrincipalResolver` Bean：把 `KmContext`（`sub`、租户）转换为业务自己的 `Authentication`（按 `sub` 关联本地用户、加载本地角色）。
2. 把 `KmIdentityFilter` 加入 Spring Security 过滤链（starter 不注册为独立 Servlet 过滤器）：

```java
http.addFilterBefore(kmIdentityFilter, UsernamePasswordAuthenticationFilter.class);
```

3. 需要账号或机构时注入 `KmDirectory`：`account(tenantId, sub)`、`accountByUsername(tenantId, username)`、`orgs(tenantId)`。
