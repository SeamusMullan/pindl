// Port of client.py — Pinterest internal resource endpoints over UXP fetch.

const BASE = "https://www.pinterest.com";

const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 " +
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
  Accept: "application/json, text/javascript, */*; q=0.01",
  "Accept-Language": "en-US,en;q=0.9",
  "X-Requested-With": "XMLHttpRequest",
  Referer: "https://www.pinterest.com/",
};

const QUALITY_PREF = ["V_1080P", "V_720P", "V_480P", "V_360P"];

function ts() {
  return String(Date.now());
}

// Parse a raw `cookie:` header value into a single Cookie request header.
// UXP fetch allows setting the Cookie header directly (unlike browser fetch).
function parseCookieString(raw) {
  return raw
    .split(";")
    .map((p) => p.trim())
    .filter((p) => p.includes("="))
    .join("; ");
}

function parseBoardUrl(url) {
  // Returns [username, boardSlug] from a Pinterest board URL.
  const path = new URL(url.trim()).pathname;
  const parts = path.split("/").filter(Boolean);
  if (parts.length < 2) {
    throw new Error(
      `Not a valid Pinterest board URL: ${url}\n` +
        "Expected: https://pinterest.com/username/board-name/"
    );
  }
  return [parts[0], parts[1]];
}

function extractVideoUrl(pin) {
  const videos = pin.videos || {};
  const videoList = videos.video_list || {};
  for (const q of QUALITY_PREF) {
    const entry = videoList[q];
    if (entry && entry.url && !entry.url.endsWith(".m3u8")) return entry.url;
  }
  for (const entry of Object.values(videoList)) {
    if (entry && entry.url && !entry.url.endsWith(".m3u8")) return entry.url;
  }
  return null;
}

async function apiGet(path, options, cookieHeader, sourceUrl) {
  const params = new URLSearchParams({
    source_url: sourceUrl,
    data: JSON.stringify({ options }),
    _: ts(),
  });
  const res = await fetch(`${BASE}${path}?${params.toString()}`, {
    method: "GET",
    headers: { ...HEADERS, Cookie: cookieHeader },
  });
  if (!res.ok) {
    throw new Error(`${path} -> HTTP ${res.status}`);
  }
  const json = await res.json();
  return json.resource_response;
}

async function getBoard(username, slug, cookieHeader) {
  const resp = await apiGet(
    "/resource/BoardResource/get/",
    { slug, username, field_set_key: "detailed" },
    cookieHeader,
    `/${username}/${slug}/`
  );
  const data = resp.data;
  return { id: data.id, name: data.name, username };
}

// Async generator: yields { pin_id, board_name, video_url } for every video pin.
async function* iterBoardVideoPins(boardId, boardName, username, cookieHeader) {
  let bookmark = null;
  while (true) {
    const options = {
      board_id: boardId,
      page_size: 25,
      field_set_key: "react_grid_pin",
    };
    if (bookmark) options.bookmarks = [bookmark];

    const resp = await apiGet(
      "/resource/BoardFeedResource/get/",
      options,
      cookieHeader,
      `/${username}/`
    );
    const pins = resp.data || [];
    if (!pins.length) break;

    for (const pin of pins) {
      const url = extractVideoUrl(pin);
      if (url) {
        yield { pin_id: pin.id, board_name: boardName, video_url: url };
      }
    }

    bookmark = resp.bookmark;
    if (!bookmark || bookmark === "-end-") break;
    await new Promise((r) => setTimeout(r, 300));
  }
}

module.exports = {
  parseCookieString,
  parseBoardUrl,
  getBoard,
  iterBoardVideoPins,
};
