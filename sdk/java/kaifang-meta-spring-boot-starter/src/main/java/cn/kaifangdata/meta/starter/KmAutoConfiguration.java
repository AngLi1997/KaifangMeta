package cn.kaifangdata.meta.starter;

import org.springframework.beans.factory.ObjectProvider;
import org.springframework.boot.autoconfigure.AutoConfiguration;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.web.servlet.FilterRegistrationBean;
import org.springframework.context.annotation.Bean;
import org.springframework.web.client.RestClient;

/**
 * kaifang-meta.enabled=true 时装配身份过滤器与身份目录；过滤器不注册为独立 Servlet 过滤器，由业务加入 Spring Security 过滤链。
 */
@AutoConfiguration
@EnableConfigurationProperties(KmProperties.class)
@ConditionalOnProperty(name = "kaifang-meta.enabled", havingValue = "true")
public class KmAutoConfiguration {

    @Bean
    KmDirectory kmDirectory(KmProperties properties, ObjectProvider<RestClient.Builder> builder) {
        properties.validate();
        return new KmDirectory(properties, builder.getIfAvailable(RestClient::builder));
    }

    @Bean
    KmIdentityFilter kmIdentityFilter(KmProperties properties, ObjectProvider<KmPrincipalResolver> resolver) {
        properties.validate();
        KmPrincipalResolver value = resolver.getIfAvailable();
        if (value == null) {
            throw new IllegalStateException("启用 kaifang-meta 时需要提供 KmPrincipalResolver：按 sub 关联本地用户");
        }
        return new KmIdentityFilter(properties, value);
    }

    @Bean
    FilterRegistrationBean<KmIdentityFilter> kmIdentityFilterRegistration(KmIdentityFilter filter) {
        FilterRegistrationBean<KmIdentityFilter> registration = new FilterRegistrationBean<>(filter);
        registration.setEnabled(false);
        return registration;
    }
}
