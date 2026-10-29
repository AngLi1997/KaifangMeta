package cn.kaifangdata.meta.starter;

import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockHttpServletRequest;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;
import java.nio.charset.StandardCharsets;
import java.util.HexFormat;

import static org.assertj.core.api.Assertions.assertThat;

class KmIdentityFilterTest {
    private static final String SECRET = "test-gateway-secret";
    private static final long NOW = 1_800_000_000_000L;
    private final KmProperties properties = new KmProperties(true, "http://gw/kaifang-meta/iam", "kaifang-meta-ub",
            "s", SECRET, "/kaifang-meta/ub", null, null);
    private final KmIdentityFilter filter = new KmIdentityFilter(properties, ctx -> null, () -> NOW);

    @Test
    void acceptsGatewaySignatureOverExternalPathAndQuery() {
        // 网关签名路径 = 前缀 + 解码后的路径 + 原始查询串
        var request = signed("/kaifang-meta/ub/platform-common/档案?a=%E4%B8%80&b=2", "/platform-common/%E6%A1%A3%E6%A1%88", "a=%E4%B8%80&b=2", NOW);
        KmContext ctx = filter.verify(request);
        assertThat(ctx).isNotNull();
        assertThat(ctx.sub()).isEqualTo("u_1");
        assertThat(ctx.tenantId()).isEqualTo("t_1");
        assertThat(ctx.isUser()).isTrue();
    }

    @Test
    void rejectsTamperedHeaderExpiredOrWrongPath() {
        var tampered = signed("/kaifang-meta/ub/prefiling/x", "/prefiling/x", null, NOW);
        tampered.removeHeader("X-KM-User-Id");
        tampered.addHeader("X-KM-User-Id", "u_2");
        assertThat(filter.verify(tampered)).isNull();

        assertThat(filter.verify(signed("/kaifang-meta/ub/prefiling/x", "/prefiling/x", null, NOW - 301_000))).isNull();
        assertThat(filter.verify(signed("/kaifang-meta/ub/prefiling/x", "/prefiling/y", null, NOW))).isNull();
    }

    private static MockHttpServletRequest signed(String signedPath, String requestUri, String query, long ts) {
        var request = new MockHttpServletRequest("GET", requestUri);
        request.setQueryString(query);
        request.addHeader("X-KM-User-Id", "u_1");
        request.addHeader("X-KM-Tenant-Id", "t_1");
        request.addHeader("X-KM-Client-Id", "kaifang-meta-ub");
        request.addHeader("X-KM-Principal-Type", "user");
        request.addHeader("X-KM-Ts", Long.toString(ts));
        request.addHeader("X-KM-Sign", hmac("GET" + signedPath + ts + "u_1" + "t_1" + "kaifang-meta-ub"));
        return request;
    }

    private static String hmac(String message) {
        try {
            Mac mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(SECRET.getBytes(StandardCharsets.UTF_8), "HmacSHA256"));
            return HexFormat.of().formatHex(mac.doFinal(message.getBytes(StandardCharsets.UTF_8)));
        } catch (Exception e) {
            throw new IllegalStateException(e);
        }
    }
}
