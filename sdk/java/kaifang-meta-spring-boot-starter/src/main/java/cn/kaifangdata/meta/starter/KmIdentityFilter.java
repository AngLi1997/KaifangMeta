package cn.kaifangdata.meta.starter;

import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.web.filter.OncePerRequestFilter;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;
import java.util.function.LongSupplier;

/**
 * 校验网关注入的 X-KM-* 身份头（docs/gateway.md「身份头与网关签名」）：
 * 签名串 = method + 网关外部路径(?query) + ts + user + tenant + client + on_behalf_of，HMAC-SHA256。
 * 没有 X-KM-Sign 的请求原样放行，交给业务其他认证方式；签名无效时不认证，由业务认证入口返回 401。
 * 使用 Spring Security 时需加入过滤链：{@code http.addFilterBefore(kmIdentityFilter, UsernamePasswordAuthenticationFilter.class)}。
 */
public class KmIdentityFilter extends OncePerRequestFilter {
    private static final Logger log = LoggerFactory.getLogger(KmIdentityFilter.class);

    private final KmProperties properties;
    private final KmPrincipalResolver resolver;
    private final byte[] secret;
    private final LongSupplier clock;

    public KmIdentityFilter(KmProperties properties, KmPrincipalResolver resolver) {
        this(properties, resolver, System::currentTimeMillis);
    }

    KmIdentityFilter(KmProperties properties, KmPrincipalResolver resolver, LongSupplier clock) {
        this.properties = properties;
        this.resolver = resolver;
        this.secret = properties.gatewaySecret().getBytes(StandardCharsets.UTF_8);
        this.clock = clock;
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        if (request.getHeader("X-KM-Sign") != null) {
            KmContext context = verify(request);
            if (context == null) {
                log.warn("网关签名身份头无效：{} {}", request.getMethod(), request.getRequestURI());
            } else {
                request.setAttribute(KmContext.ATTRIBUTE, context);
                Authentication authentication = resolver.resolve(context);
                if (authentication != null) {
                    SecurityContextHolder.getContext().setAuthentication(authentication);
                }
            }
        }
        chain.doFilter(request, response);
    }

    KmContext verify(HttpServletRequest request) {
        String user = header(request, "X-KM-User-Id");
        String tenant = header(request, "X-KM-Tenant-Id");
        String client = header(request, "X-KM-Client-Id");
        String onBehalfOf = header(request, "X-KM-On-Behalf-Of");
        String ts = header(request, "X-KM-Ts");
        String sign = header(request, "X-KM-Sign");
        if (user.isEmpty() || !ts.matches("\\d{1,15}")) {
            return null;
        }
        if (Math.abs(clock.getAsLong() - Long.parseLong(ts)) > properties.signWindow()) {
            return null;
        }
        // APISIX 在 proxy-rewrite 去前缀之前签名，签名路径为网关外部路径
        String prefix = properties.gatewayPrefix() == null ? "" : properties.gatewayPrefix().replaceAll("/$", "");
        // 网关签名用解码后的路径（ngx.var.uri）与原始查询串（ngx.var.args）
        String query = request.getQueryString();
        String path = prefix + decode(request.getRequestURI()) + (query == null || query.isEmpty() ? "" : "?" + query);
        String message = request.getMethod() + path + ts + user + tenant + client + onBehalfOf;
        byte[] expected = hmac(message).getBytes(StandardCharsets.US_ASCII);
        if (!MessageDigest.isEqual(expected, sign.getBytes(StandardCharsets.US_ASCII))) {
            return null;
        }
        return new KmContext(user, tenant, client, header(request, "X-KM-Principal-Type"),
                header(request, "X-KM-Request-Id"), onBehalfOf);
    }

    private String hmac(String message) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(secret, "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(message.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException("HMAC-SHA256 unavailable", e);
        }
    }

    private static String decode(String uri) {
        try {
            return new java.net.URI(uri).getPath();
        } catch (java.net.URISyntaxException e) {
            return uri;
        }
    }

    private static String header(HttpServletRequest request, String name) {
        String value = request.getHeader(name);
        return value == null ? "" : value;
    }
}
