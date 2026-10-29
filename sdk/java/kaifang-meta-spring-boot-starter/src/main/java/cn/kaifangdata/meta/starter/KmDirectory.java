package cn.kaifangdata.meta.starter;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.web.client.HttpClientErrorException;
import org.springframework.web.client.RestClient;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Supplier;

/**
 * 平台身份目录（scope directory:read）：按 sub / 登录名查账号，查当前租户机构。
 * 以应用的 Service Token 调用，Token 按租户缓存并在到期前 60 秒续期；查询结果本地缓存（账号 60 秒、机构 5 分钟）。
 */
public class KmDirectory {
    private static final Duration ACCOUNT_TTL = Duration.ofSeconds(60);
    private static final Duration ORG_TTL = Duration.ofMinutes(5);

    private final KmProperties properties;
    private final RestClient http;
    private final Map<String, Cached<?>> cache = new ConcurrentHashMap<>();

    public KmDirectory(KmProperties properties, RestClient.Builder builder) {
        this.properties = properties;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(2));
        factory.setReadTimeout(Duration.ofSeconds(5));
        this.http = builder.requestFactory(factory).build();
    }

    /** 账号不存在或不属于该租户时返回 null */
    public Account account(String tenantId, String sub) {
        return cached("account:" + tenantId + ":" + sub, ACCOUNT_TTL,
                () -> data(get(tenantId, "/accounts/{sub}", AccountResponse.class, sub)));
    }

    public Account accountByUsername(String tenantId, String username) {
        return cached("username:" + tenantId + ":" + username, ACCOUNT_TTL,
                () -> data(get(tenantId, "/accounts?username={username}", AccountResponse.class, username)));
    }

    private static Account data(AccountResponse response) {
        return response == null ? null : response.data();
    }

    public List<Org> orgs(String tenantId) {
        OrgsResponse response = cached("orgs:" + tenantId, ORG_TTL, () -> {
            OrgsResponse value = get(tenantId, "/orgs", OrgsResponse.class);
            return value == null ? new OrgsResponse(List.of()) : value;
        });
        return response.data();
    }

    /** 本地缓存失效，例如收到 org.changed / user.updated 后 */
    public void evict() {
        cache.keySet().removeIf(key -> !key.startsWith("token:"));
    }

    private <T> T get(String tenantId, String uri, Class<T> type, Object... vars) {
        try {
            return http.get().uri(properties.directoryUrl() + uri, vars)
                    .header("Authorization", "Bearer " + token(tenantId))
                    .retrieve().body(type);
        } catch (HttpClientErrorException e) {
            if (e.getStatusCode() == HttpStatus.NOT_FOUND) {
                return null;
            }
            throw e;
        }
    }

    private String token(String tenantId) {
        TokenResponse token = cached("token:" + tenantId, null, () -> {
            var form = new LinkedMultiValueMap<String, String>();
            form.add("grant_type", "client_credentials");
            form.add("tenant", tenantId);
            form.add("scope", "directory:read");
            return http.post().uri(properties.issuer() + "/token")
                    .headers(h -> h.setBasicAuth(properties.clientId(), properties.clientSecret()))
                    .contentType(MediaType.APPLICATION_FORM_URLENCODED).body(form)
                    .retrieve().body(TokenResponse.class);
        });
        return token.accessToken();
    }

    @SuppressWarnings("unchecked")
    private <T> T cached(String key, Duration ttl, Supplier<T> loader) {
        long now = System.currentTimeMillis();
        Cached<?> hit = cache.get(key);
        if (hit != null && hit.expiresAt() > now) {
            return (T) hit.value();
        }
        T value = loader.get();
        if (value != null) {
            long expiresAt = ttl != null ? now + ttl.toMillis()
                    : now + (((TokenResponse) value).expiresIn() - 60) * 1000L;
            cache.put(key, new Cached<>(value, expiresAt));
        }
        return value;
    }

    private record Cached<T>(T value, long expiresAt) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    record TokenResponse(@JsonProperty("access_token") String accessToken, @JsonProperty("expires_in") long expiresIn) {
    }

    /** 身份账号基础字段；orgId 为所属机构 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Account(String sub, @JsonProperty("tenant_id") String tenantId, String username, String name,
            String email, String phone, @JsonProperty("org_id") Long orgId, String status) {
        public boolean active() {
            return "active".equals(status);
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    record AccountResponse(Account data) {
    }

    /** 机构；level 按上级关系计算，根为 1 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Org(long id, @JsonProperty("parent_id") Long parentId, String code, String name, int level,
            @JsonProperty("sort_order") int sortOrder, String status) {
        public boolean active() {
            return "active".equals(status);
        }
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    record OrgsResponse(List<Org> data) {
    }
}
