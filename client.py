import asyncio
import json
import time
from typing import AsyncGenerator, Optional

import httpx

BASE = "https://www.pinterest.com"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.pinterest.com/",
}
_QUALITY_PREF = ["V_1080P", "V_720P", "V_480P", "V_360P"]


def _extract_video_url(pin: dict) -> Optional[str]:
    videos = pin.get("videos") or {}
    video_list = videos.get("video_list") or {}
    for quality in _QUALITY_PREF:
        entry = video_list.get(quality)
        if entry:
            url = entry.get("url", "")
            if url and not url.endswith(".m3u8"):
                return url
    # fallback: any non-HLS URL
    for entry in video_list.values():
        url = entry.get("url", "")
        if url and not url.endswith(".m3u8"):
            return url
    return None


def _ts() -> str:
    return str(int(time.time() * 1000))


async def get_user(username: str, cookies: dict) -> dict:
    params = {
        "source_url": f"/{username}/",
        "data": json.dumps({"options": {"username": username, "field_set_key": "unauth_profile"}}),
        "_": _ts(),
    }
    async with httpx.AsyncClient(headers=_HEADERS, cookies=cookies, follow_redirects=True, timeout=20.0) as c:
        r = await c.get(f"{BASE}/resource/UserResource/get/", params=params)
        r.raise_for_status()
        data = r.json()["resource_response"]["data"]
        return {
            "id": data["id"],
            "username": data["username"],
            "full_name": data.get("full_name", ""),
        }


def parse_board_url(url: str) -> tuple[str, str]:
    """Returns (username, board_slug) from a Pinterest board URL."""
    from urllib.parse import urlparse
    parts = [p for p in urlparse(url.strip()).path.split("/") if p]
    if len(parts) < 2:
        raise ValueError(f"Not a valid Pinterest board URL: {url!r}\nExpected: https://pinterest.com/username/board-name/")
    return parts[0], parts[1]


async def get_board(username: str, slug: str, cookies: dict) -> dict:
    """Returns {"id", "name"} for a specific board by URL slug."""
    params = {
        "source_url": f"/{username}/{slug}/",
        "data": json.dumps({"options": {
            "slug": slug,
            "username": username,
            "field_set_key": "detailed",
        }}),
        "_": _ts(),
    }
    async with httpx.AsyncClient(headers=_HEADERS, cookies=cookies, follow_redirects=True, timeout=20.0) as c:
        r = await c.get(f"{BASE}/resource/BoardResource/get/", params=params)
        r.raise_for_status()
        data = r.json()["resource_response"]["data"]
        return {"id": data["id"], "name": data["name"], "username": username}


async def get_boards(user_id: str, username: str, cookies: dict) -> list[dict]:
    params = {
        "source_url": f"/{username}/",
        "data": json.dumps({"options": {
            "user_id": user_id,
            "page_size": 100,
            "privacy_filter": "all",
            "field_set_key": "detailed",
        }}),
        "_": _ts(),
    }
    async with httpx.AsyncClient(headers=_HEADERS, cookies=cookies, follow_redirects=True, timeout=20.0) as c:
        r = await c.get(f"{BASE}/resource/BoardsResource/get/", params=params)
        r.raise_for_status()
        boards = r.json()["resource_response"]["data"]
        return [
            {
                "id": b["id"],
                "name": b["name"],
                "slug": b.get("url", "").strip("/").split("/")[-1],
                "pin_count": b.get("pin_count", 0),
            }
            for b in boards
        ]


async def iter_board_video_pins(
    board_id: str,
    board_name: str,
    username: str,
    cookies: dict,
) -> AsyncGenerator[dict, None]:
    bookmark: Optional[str] = None
    async with httpx.AsyncClient(headers=_HEADERS, cookies=cookies, follow_redirects=True, timeout=30.0) as c:
        while True:
            options: dict = {
                "board_id": board_id,
                "page_size": 25,
                "field_set_key": "react_grid_pin",
            }
            if bookmark:
                options["bookmarks"] = [bookmark]
            params = {
                "source_url": f"/{username}/",
                "data": json.dumps({"options": options}),
                "_": _ts(),
            }
            r = await c.get(f"{BASE}/resource/BoardFeedResource/get/", params=params)
            r.raise_for_status()
            resp = r.json()["resource_response"]
            pins = resp.get("data") or []
            if not pins:
                break
            for pin in pins:
                url = _extract_video_url(pin)
                if url:
                    yield {"pin_id": pin["id"], "board_name": board_name, "video_url": url}
            bookmark = resp.get("bookmark")
            if not bookmark or bookmark == "-end-":
                break
            await asyncio.sleep(0.3)
