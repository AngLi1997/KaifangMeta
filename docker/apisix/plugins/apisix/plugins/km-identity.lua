-- km-identity：模式 A 网关托管（docs/gateway.md「身份头与网关签名」「网关插件链」）
-- 在 openid-connect 完成 JWKS 验签之后运行，合并了 km-strip-headers / km-audience / km-revoke / km-tenant / km-scope：
-- 清洗 X-KM-* → aud → 吊销 → 租户开通 → scope / 调用方 → 注入身份头与签名 → 删除 Authorization
-- 失败语义见 docs/auth-flow.md「失败语义」
local core = require("apisix.core")
local hmac = require("resty.openssl.hmac")
local to_hex = require("resty.string").to_hex
local redis = require("resty.redis")
local ngx = ngx

local schema = {
    type = "object",
    properties = {
        aud = { type = "string" },
        secret = { type = "string" },
        redis_host = { type = "string", default = "redis" },
        redis_port = { type = "integer", default = 6379 },
        redis_timeout = { type = "integer", default = 200 },
        -- 开通该应用的租户；为空表示不校验（平台 API 服务所有租户）
        tenants = { type = "array", items = { type = "string" }, default = {} },
        -- 该路由要求的 scope（平台 API 路由）
        scopes = { type = "array", items = { type = "string" }, default = {} },
        -- 业务间调用允许列表（Service Token 的调用方）；为空表示不校验
        callers = { type = "array", items = { type = "string" }, default = {} },
        -- 只在平台 API 路由识别 X-KM-On-Behalf-Of，其他路由一律删除
        allow_on_behalf_of = { type = "boolean", default = false },
    },
    required = { "aud", "secret" },
}

local _M = {
    version = 0.1,
    priority = 2590, -- 低于 openid-connect(2599)，在其验签之后执行
    name = "km-identity",
    schema = schema,
}

function _M.check_schema(conf)
    return core.schema.check(schema, conf)
end

local function jwt_payload(token)
    local seg = token:match("^[^.]+%.([^.]+)%.")
    if not seg then
        return nil
    end
    seg = seg:gsub("-", "+"):gsub("_", "/")
    seg = seg .. string.rep("=", (4 - #seg % 4) % 4)
    local raw = ngx.decode_base64(seg)
    return raw and core.json.decode(raw)
end

local function contains(list, value)
    if type(list) == "string" then
        return list == value
    end
    for _, v in ipairs(list or {}) do
        if v == value then
            return true
        end
    end
    return false
end

local function fail(status, error_code, msg)
    return status, { code = error_code, msg = msg }
end

-- 返回 true 表示已吊销；Redis 不可用时降级放行并告警（短有效期兜底）
local function revoked(conf, sid, sub, tenant)
    local red = redis:new()
    red:set_timeout(conf.redis_timeout)
    local ok, err = red:connect(conf.redis_host, conf.redis_port)
    if not ok then
        core.log.warn("km-identity: redis 不可用，降级放行: ", err)
        return false
    end
    local res, qerr = red:exists(
        "km:revoke:sid:" .. (sid or ""),
        "km:revoke:sub:" .. (sub or ""),
        "km:revoke:tenant:" .. (tenant or "")
    )
    red:set_keepalive(10000, 100)
    if not res then
        core.log.warn("km-identity: 吊销查询失败，降级放行: ", qerr)
        return false
    end
    return res > 0
end

function _M.rewrite(conf, ctx)
    local obo = conf.allow_on_behalf_of and core.request.header(ctx, "X-KM-On-Behalf-Of") or ""
    for name, _ in pairs(ngx.req.get_headers()) do
        if name:lower():sub(1, 5) == "x-km-" then
            core.request.set_header(ctx, name, nil)
        end
    end

    local auth = core.request.header(ctx, "Authorization") or ""
    local claims = jwt_payload(auth:match("^[Bb]earer%s+(.+)$") or "")
    if not claims or not claims.sub then
        return fail(401, "TOKEN_INVALID", "无效的 Token")
    end
    if not contains(claims.aud, conf.aud) then
        return fail(403, "AUDIENCE_MISMATCH", "Token 不属于该应用")
    end
    local tenant = claims.tid or ""
    if revoked(conf, claims.sid, claims.sub, tenant) then
        return fail(401, "SESSION_REVOKED", "登录已失效")
    end

    if #conf.tenants > 0 and not contains(conf.tenants, tenant) then
        return fail(403, "TENANT_NOT_ENABLED", "当前租户未开通该应用")
    end

    local granted = {}
    for scope in (claims.scope or ""):gmatch("%S+") do
        granted[scope] = true
    end
    for _, scope in ipairs(conf.scopes) do
        if not granted[scope] then
            return fail(403, "SCOPE_DENIED", "缺少 scope: " .. scope)
        end
    end

    local principal = claims.km_principal == "service" and "service" or "user"
    -- 换取的代表用户 Token 记录真实调用方（act.sub）
    local client = (claims.act and claims.act.sub) or claims.azp or ""
    if principal == "service" and #conf.callers > 0 and not contains(conf.callers, client) then
        return fail(403, "CALLER_DENIED", "调用方不在允许列表")
    end
    if obo ~= "" and (principal ~= "service" or not granted["delegate:user"]) then
        return fail(403, "SCOPE_DENIED", "代表用户需要 Service Token 与 delegate:user")
    end

    local user = claims.sub
    local ts = tostring(math.floor(ngx.now() * 1000))
    local mac = hmac.new(conf.secret, "sha256")
    -- 签名覆盖查询参数，防止截获后改参数重放
    local args = ctx.var.args
    local path = ctx.var.uri .. ((args and args ~= "") and ("?" .. args) or "")
    local sign = to_hex(mac:final(ctx.var.request_method .. path .. ts .. user .. tenant .. client .. obo))

    core.request.set_header(ctx, "X-KM-User-Id", user)
    core.request.set_header(ctx, "X-KM-Tenant-Id", tenant)
    core.request.set_header(ctx, "X-KM-Client-Id", client)
    core.request.set_header(ctx, "X-KM-Principal-Type", principal)
    core.request.set_header(ctx, "X-KM-Request-Id", ctx.var.request_id)
    core.request.set_header(ctx, "X-KM-Ts", ts)
    core.request.set_header(ctx, "X-KM-Sign", sign)
    if obo ~= "" then
        core.request.set_header(ctx, "X-KM-On-Behalf-Of", obo)
    end
    core.request.set_header(ctx, "Authorization", nil)
end

return _M
