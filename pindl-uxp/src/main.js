// Wires the panel UI: fetch board video pins -> download -> import into Premiere.

const { parseCookieString, parseBoardUrl, getBoard, iterBoardVideoPins } =
  require("./client.js");
const { downloadAll } = require("./downloader.js");
const premiere = require("./premiere.js");

const fs = require("uxp").storage.localFileSystem;

const IMPORT_BIN = "pindl";

let outputFolder = null; // UXP folder entry

const $ = (id) => document.getElementById(id);

function log(msg, cls) {
  const el = $("log");
  const line = document.createElement("div");
  if (cls) line.className = cls;
  line.textContent = msg;
  el.appendChild(line);
  el.scrollTop = el.scrollHeight;
}

function setBusy(busy) {
  $("download").disabled = busy;
  $("chooseFolder").disabled = busy;
}

async function chooseFolder() {
  const folder = await fs.getFolder();
  if (folder) {
    outputFolder = folder;
    $("folderLabel").textContent = `Output: ${folder.nativePath}`;
    $("folderLabel").className = "";
  }
}

async function run() {
  const url = $("url").value.trim();
  const rawCookie = $("cookie").value.trim();
  const doImport = $("importToggle").checked;

  if (!url) return log("Enter a board URL.", "err");
  if (!rawCookie) return log("Paste your Pinterest cookie string.", "err");
  if (!outputFolder) return log("Choose an output folder first.", "err");

  setBusy(true);
  $("log").textContent = "";

  try {
    const cookieHeader = parseCookieString(rawCookie);
    const [username, slug] = parseBoardUrl(url);

    log(`Resolving board ${username}/${slug}…`);
    const board = await getBoard(username, slug, cookieHeader);
    log(`Board: ${board.name} (${board.id})`);

    log("Scanning for video pins…");
    const pins = [];
    for await (const pin of iterBoardVideoPins(
      board.id,
      board.name,
      username,
      cookieHeader
    )) {
      pins.push(pin);
      if (pins.length % 25 === 0) log(`  found ${pins.length} videos…`, "muted");
    }
    log(`Found ${pins.length} video pin(s).`);
    if (!pins.length) return;

    const progress = (status, pin, info) => {
      const tag = { ok: "✓", skip: "•", error: "✗" }[status] || "?";
      log(`${tag} ${pin.pin_id} ${status === "error" ? info : ""}`, status);
    };

    log("Downloading…");
    const { ok, skip, errors, paths } = await downloadAll(
      pins,
      outputFolder,
      progress
    );
    log(`Done: ${ok} downloaded, ${skip} skipped, ${errors.length} errors.`,
      errors.length ? "err" : "ok");

    if (doImport && paths.length) {
      if (!premiere.isAvailable()) {
        log("Premiere DOM unavailable — skipped import.", "err");
      } else {
        log(`Importing ${paths.length} clip(s) into bin "${IMPORT_BIN}"…`);
        try {
          const n = await premiere.importFiles(paths, IMPORT_BIN);
          log(`Imported ${n} clip(s).`, "ok");
        } catch (e) {
          log(`Import failed: ${e.message}`, "err");
        }
      }
    }
  } catch (e) {
    log(`Error: ${e.message}`, "err");
  } finally {
    setBusy(false);
  }
}

$("chooseFolder").addEventListener("click", chooseFolder);
$("download").addEventListener("click", run);
