import asyncio
import re
from pathlib import Path
from typing import Callable, Optional

import httpx

_SEMAPHORE = 4
_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Referer": "https://www.pinterest.com/",
}


def _safe(s: str) -> str:
    return re.sub(r'[\\/*?:"<>|]', "_", s)


def _dest(output_dir: Path, pin_id: str, board_name: str) -> Path:
    return output_dir / f"{pin_id}_{_safe(board_name)}.mp4"


async def _download_one(
    client: httpx.AsyncClient,
    sem: asyncio.Semaphore,
    pin: dict,
    output_dir: Path,
    progress_cb: Optional[Callable],
) -> tuple[str, str]:
    path = _dest(output_dir, pin["pin_id"], pin["board_name"])
    if path.exists():
        if progress_cb:
            progress_cb("skip", pin, path)
        return ("skip", str(path))
    async with sem:
        try:
            async with client.stream("GET", pin["video_url"]) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    async for chunk in r.aiter_bytes(65536):
                        f.write(chunk)
            if progress_cb:
                progress_cb("ok", pin, path)
            return ("ok", str(path))
        except Exception as e:
            if progress_cb:
                progress_cb("error", pin, str(e))
            return ("error", str(e))


async def download_all(
    pins: list[dict],
    output_dir: Path,
    progress_cb: Optional[Callable] = None,
) -> tuple[int, int, list[str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    sem = asyncio.Semaphore(_SEMAPHORE)
    async with httpx.AsyncClient(headers=_HEADERS, follow_redirects=True, timeout=60.0) as client:
        results = await asyncio.gather(
            *[_download_one(client, sem, pin, output_dir, progress_cb) for pin in pins]
        )
    ok = sum(1 for r in results if r[0] == "ok")
    skip = sum(1 for r in results if r[0] == "skip")
    errors = [r[1] for r in results if r[0] == "error"]
    return ok, skip, errors
