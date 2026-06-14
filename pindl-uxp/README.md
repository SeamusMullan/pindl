# pindl-uxp

Premiere Pro UXP plugin port of [pindl](../). Downloads every video pin from a
Pinterest board and imports the clips straight into your active project.

## What it does

1. Resolve a board URL via Pinterest's internal resource endpoints.
2. Page through the board feed, collecting non-HLS `.mp4` URLs (best quality first).
3. Download up to 4 concurrently into a folder you pick.
4. Import the downloads into a `pindl` bin in the active Premiere project.

## Differences from the Python tool

- **Auth is manual only.** The Python version auto-reads browser cookies via
  `browser_cookie3`. The UXP sandbox can't crack the encrypted browser cookie
  store, so you paste the `cookie:` header yourself (devtools › Network › any
  pinterest.com request › copy the `cookie` header value).
- **No streaming to disk.** UXP filesystem has no chunked writer, so each video
  is buffered in memory then written. Fine for typical clips.
- **Auto-import** into the project — the reason to be a plugin vs. a standalone app.

## Install (development)

1. Install [UXP Developer Tool](https://developer.adobe.com/photoshop/uxp/2022/guides/devtool/)
   (UDT) from Creative Cloud.
2. UDT › **Add Plugin** › select `pindl-uxp/manifest.json`.
3. With Premiere Pro running, click **Load** in UDT.
4. Panel appears under **Window › Extensions (or UXP) › pindl**.

## Build

```
./build.sh
```

Validates the manifest + JS, then writes `dist/pindl-uxp-<version>.zip` — the
unsigned bundle the UXP Developer Tool loads. Bump `version` in `manifest.json`
before each QA drop so testers can tell builds apart.

## Send to QA

QA testers have **no dev setup**, so they need a signed `.ccx` they can
double-click (Creative Cloud installs it via the Plugin Installer). UXP signing
lives in the UXP Developer Tool, so the signed artifact is produced there:

1. `./build.sh` (catches errors before packaging).
2. UDT › add `manifest.json` › **••• › Package**.
3. UDT signs it (self-signed cert is fine for testing) and writes `pindl.ccx`.
4. Send `pindl.ccx` to QA. They double-click → installs into Premiere. Panel
   shows under **Window › UXP/Extensions › pindl**.

Each tester also needs:

- A Pinterest **cookie string** (devtools › Network › any pinterest.com request
  › copy `cookie` header value). No login flow in the plugin.
- The **board URL** to test against.

> Self-signed `.ccx` installs only on machines with Creative Cloud plugin
> developer/test mode allowed. For a build that installs cleanly everywhere,
> submit through the Adobe Marketplace (production signing). Use that route once
> QA signs off.

### QA test checklist

- [ ] Plugin installs from `.ccx` and panel opens.
- [ ] Valid board URL + cookie → scan finds expected video count.
- [ ] Downloads land in chosen folder; re-run skips existing files.
- [ ] Import toggle ON → clips appear in `pindl` bin of active project.
- [ ] Import toggle OFF → no project changes.
- [ ] No project open → graceful error, downloads still saved.
- [ ] Bad/expired cookie → clear error, no crash.

## Notes / TODO

- `manifest.json` `host.minVersion` (`25.0.0`) and the `premierepro` import API
  in `src/premiere.js` track Premiere's evolving UXP DOM — bump/adjust to match
  your installed version if `importFiles` / `createBin` signatures differ.
- Pinterest endpoints are unofficial and may change (same risk as the Python tool).
- Network domains are whitelisted in `manifest.json` (`requiredPermissions.network.domains`).
