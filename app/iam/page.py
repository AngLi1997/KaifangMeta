from html import escape

from fastapi.responses import HTMLResponse

STYLE = """
:root{--bg:#f5f6f8;--card:#fff;--text:#1f2329;--muted:#8f959e;--line:#dee0e3;--primary:#f4511e;--danger:#d83931}
@media (prefers-color-scheme:dark){:root{--bg:#141414;--card:#1f1f1f;--text:#e8e8e8;--muted:#8a8a8a;--line:#3a3a3a}}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;display:flex;align-items:center;justify-content:center;
background:var(--bg);color:var(--text);font:15px/1.5 -apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;padding:16px}
form{width:100%;max-width:360px;background:var(--card);border-radius:10px;padding:36px 28px;box-shadow:0 8px 24px rgba(0,0,0,.08)}
h1{margin:0 0 28px;font-size:22px;font-weight:600;text-align:center}
input{display:block;width:100%;height:44px;margin-bottom:16px;padding:0 12px;border:1px solid var(--line);border-radius:6px;
background:transparent;color:var(--text);font-size:15px}
input:focus{outline:none;border-color:var(--primary)}
button{width:100%;height:44px;border:0;border-radius:6px;background:var(--primary);color:#fff;font-size:15px;cursor:pointer}
.err{color:var(--danger);font-size:13px;margin:-4px 0 12px}
.tenant{background:transparent;color:var(--text);border:1px solid var(--line);margin-bottom:12px;text-align:left;padding:0 14px}
.tenant:hover,.tenant.current{border-color:var(--primary)}
"""


def login_page(query: str, username: str = "", error: str = "") -> HTMLResponse:
    err = f'<p class="err" role="alert">{escape(error)}</p>' if error else ""
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>登录 | KaifangMetaPlatform</title><style>{STYLE}</style></head>
<body><form method="post" action="/kaifang-meta/iam/login">
<h1>KaifangMetaPlatform</h1>
<input name="username" value="{escape(username)}" placeholder="账号" aria-label="账号" autocomplete="username" required autofocus>
<input name="password" type="password" placeholder="密码" aria-label="密码" autocomplete="current-password" required>
{err}<input type="hidden" name="q" value="{escape(query)}">
<button type="submit">登录</button>
</form></body></html>"""
    return HTMLResponse(html, status_code=401 if error else 200)


def tenant_page(params: dict, tenants: list[tuple[str, str]], current: str = "") -> HTMLResponse:
    """多租户账号选择本次登录的租户：带上原授权参数重新 GET /authorize"""
    hidden = "".join(
        f'<input type="hidden" name="{escape(k)}" value="{escape(v)}">'
        for k, v in params.items()
        if k not in ("tenant", "prompt")
    )
    buttons = "".join(
        f'<button class="tenant{" current" if tid == current else ""}" name="tenant" value="{escape(tid)}">{escape(name)}</button>'
        for tid, name in tenants
    )
    html = f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>选择租户 | KaifangMetaPlatform</title><style>{STYLE}</style></head>
<body><form method="get" action="/kaifang-meta/iam/authorize">
<h1>选择租户</h1>{hidden}{buttons}
</form></body></html>"""
    return HTMLResponse(html)


def message_page(title: str, message: str = "", status_code: int = 400) -> HTMLResponse:
    msg = f'<p class="err" role="alert">{escape(message)}</p>' if message else ""
    html = f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>{STYLE}</style></head>
<body><form><h1>{escape(title)}</h1>{msg}</form></body></html>"""
    return HTMLResponse(html, status_code=status_code)
