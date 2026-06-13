try:
    import browser_cookie3
    _HAS_BROWSER_COOKIE3 = True
except ImportError:
    _HAS_BROWSER_COOKIE3 = False


def get_cookies_auto() -> dict:
    if not _HAS_BROWSER_COOKIE3:
        raise RuntimeError("browser-cookie3 not installed. Run: pip install browser-cookie3")

    loaders = [
        browser_cookie3.chrome,
        browser_cookie3.chromium,
        browser_cookie3.firefox,
        browser_cookie3.edge,
        browser_cookie3.safari,
    ]
    for loader in loaders:
        try:
            jar = loader(domain_name="pinterest.com")
            cookies = {c.name: c.value for c in jar}
            if "_auth" in cookies:
                return cookies
        except Exception:
            continue
    raise RuntimeError(
        "No Pinterest session found in any browser. "
        "Log into Pinterest in Chrome or Firefox first, then try again."
    )


def parse_cookie_string(raw: str) -> dict:
    result = {}
    for pair in raw.split(";"):
        pair = pair.strip()
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result
