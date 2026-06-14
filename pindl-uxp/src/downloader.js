// Port of downloader.py — concurrent mp4 download into a UXP folder entry.

const { formats } = require("uxp").storage;

const SEMAPHORE = 4;

const HEADERS = {
  "User-Agent":
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
  Referer: "https://www.pinterest.com/",
};

function safe(s) {
  return s.replace(/[\\/*?:"<>|]/g, "_");
}

function destName(pinId, boardName) {
  return `${pinId}_${safe(boardName)}.mp4`;
}

async function fileExists(folder, name) {
  try {
    await folder.getEntry(name);
    return true;
  } catch {
    return false;
  }
}

async function downloadOne(folder, pin, progressCb) {
  const name = destName(pin.pin_id, pin.board_name);

  if (await fileExists(folder, name)) {
    progressCb && progressCb("skip", pin, name);
    return { status: "skip", value: name };
  }

  try {
    const res = await fetch(pin.video_url, { method: "GET", headers: HEADERS });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    // UXP filesystem has no streaming writer; buffer then write.
    const buf = await res.arrayBuffer();
    const file = await folder.createFile(name, { overwrite: true });
    await file.write(buf, { format: formats.binary });

    const nativePath = file.nativePath; // absolute path for Premiere import
    progressCb && progressCb("ok", pin, nativePath);
    return { status: "ok", value: nativePath };
  } catch (e) {
    progressCb && progressCb("error", pin, String(e.message || e));
    return { status: "error", value: String(e.message || e) };
  }
}

// Promise pool capped at SEMAPHORE concurrent downloads.
async function downloadAll(pins, folder, progressCb) {
  const results = [];
  let idx = 0;

  async function worker() {
    while (idx < pins.length) {
      const i = idx++;
      results[i] = await downloadOne(folder, pins[i], progressCb);
    }
  }

  const workers = Array.from(
    { length: Math.min(SEMAPHORE, pins.length) },
    worker
  );
  await Promise.all(workers);

  const ok = results.filter((r) => r.status === "ok");
  const skip = results.filter((r) => r.status === "skip");
  const errors = results.filter((r) => r.status === "error").map((r) => r.value);
  const paths = ok.map((r) => r.value);

  return { ok: ok.length, skip: skip.length, errors, paths };
}

module.exports = { downloadAll };
