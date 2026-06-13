# pindl

Bulk-download videos from a Pinterest board.

## Usage

**GUI** — paste a board URL, pick an output folder, click Download:

```
uv run python main.py
```

**CLI:**

```
uv run python main.py --no-gui --url https://www.pinterest.com/you/your-board/
```

## Auth

The tool reads your Pinterest session cookie automatically from Chrome, Firefox, or Edge. Just be logged into Pinterest in your browser before running.

If auto-detect fails, select "Paste cookie string" in the GUI (or pass `--cookie "..."` in CLI) and paste the `cookie:` header value from any pinterest.com request in your browser's devtools Network tab.

## Install

```
uv sync
```

## Build binary

```
uv run pyinstaller --onefile --name pindl main.py
```

Pre-built binaries for Linux, Windows, and macOS are attached to each [GitHub Release](../../releases).
