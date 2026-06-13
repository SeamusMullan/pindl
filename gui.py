import asyncio
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk
from typing import Optional

from auth import get_cookies_auto, parse_cookie_string
from client import get_board, iter_board_video_pins, parse_board_url
from downloader import download_all


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("pindl — Pinterest Video Downloader")
        self.resizable(False, False)
        self._cookies: Optional[dict] = None
        self._build_ui()

    def _build_ui(self):
        pad = {"padx": 12, "pady": 6}

        # Board URL row
        row = ttk.Frame(self)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Board URL:", width=16, anchor="w").pack(side="left")
        self.url_var = tk.StringVar()
        ttk.Entry(row, textvariable=self.url_var, width=40).pack(side="left")

        ttk.Label(
            self,
            text="e.g. https://www.pinterest.com/yourname/your-board/",
            foreground="grey",
            anchor="w",
        ).pack(fill="x", padx=12)

        # Output dir row
        row = ttk.Frame(self)
        row.pack(fill="x", **pad)
        ttk.Label(row, text="Output Folder:", width=16, anchor="w").pack(side="left")
        self.output_var = tk.StringVar(value=str(Path.home() / "pinterest_downloads"))
        ttk.Entry(row, textvariable=self.output_var, width=40).pack(side="left")
        ttk.Button(row, text="Browse…", command=self._browse).pack(side="left", padx=6)

        # Auth mode
        auth_frame = ttk.LabelFrame(self, text="Authentication")
        auth_frame.pack(fill="x", **pad)
        self.auth_mode = tk.StringVar(value="auto")
        ttk.Radiobutton(
            auth_frame, text="Auto-detect from browser (Chrome / Firefox / Edge)",
            variable=self.auth_mode, value="auto",
        ).pack(anchor="w", padx=6, pady=2)
        ttk.Radiobutton(
            auth_frame, text="Paste cookie string manually",
            variable=self.auth_mode, value="manual",
        ).pack(anchor="w", padx=6)
        self.auth_mode.trace_add("write", self._toggle_cookie_frame)

        # Manual cookie input (hidden initially)
        self._cookie_outer = ttk.Frame(self)
        ttk.Label(
            self._cookie_outer,
            text="Cookie string (browser devtools → Network tab → any pinterest.com request → cookie header):",
            wraplength=460,
        ).pack(anchor="w", padx=12)
        self.cookie_text = tk.Text(self._cookie_outer, height=3, width=56, wrap="word")
        self.cookie_text.pack(fill="x", padx=12, pady=(0, 4))

        # Download button
        self._dl_btn = ttk.Button(self, text="Download Videos", command=self._start)
        self._dl_btn.pack(**pad)

        # Progress
        self.progress_var = tk.DoubleVar()
        ttk.Progressbar(self, variable=self.progress_var, maximum=100, length=460).pack(**pad)
        self.status_var = tk.StringVar(value="Paste a board URL and click Download.")
        ttk.Label(self, textvariable=self.status_var, anchor="w", wraplength=460).pack(fill="x", padx=12)

        # Log
        log_frame = ttk.LabelFrame(self, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log = scrolledtext.ScrolledText(log_frame, height=8, state="disabled", wrap="word")
        self.log.pack(fill="both", expand=True, padx=4, pady=4)

    def _toggle_cookie_frame(self, *_):
        if self.auth_mode.get() == "manual":
            self._cookie_outer.pack(fill="x", padx=0, pady=0, before=self._dl_btn)
        else:
            self._cookie_outer.pack_forget()

    def _browse(self):
        d = filedialog.askdirectory(initialdir=self.output_var.get())
        if d:
            self.output_var.set(d)

    def _log(self, msg: str):
        self.log.config(state="normal")
        self.log.insert("end", msg + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    def _status(self, msg: str):
        self.status_var.set(msg)
        self._log(msg)

    def _get_cookies(self) -> dict:
        if self.auth_mode.get() == "auto":
            return get_cookies_auto()
        raw = self.cookie_text.get("1.0", "end").strip()
        if not raw:
            raise ValueError("Paste your Pinterest cookie string first.")
        return parse_cookie_string(raw)

    def _start(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Paste a Pinterest board URL first.")
            return
        try:
            username, slug = parse_board_url(url)
            cookies = self._get_cookies()
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        self._cookies = cookies
        self._dl_btn.config(state="disabled")
        self.progress_var.set(0)
        self._status(f"Connecting to pinterest.com/{username}/{slug}/…")
        threading.Thread(target=self._worker, args=(username, slug), daemon=True).start()

    def _worker(self, username: str, slug: str):
        async def run():
            board = await get_board(username, slug, self._cookies)
            self.after(0, self._status, f"Board: {board['name']}. Scanning for video pins…")

            pins: list[dict] = []
            async for pin in iter_board_video_pins(board["id"], board["name"], username, self._cookies):
                pins.append(pin)
                self.after(0, self.status_var.set, f"Found {len(pins)} video pin(s)…")

            if not pins:
                self.after(0, self._status, f"No video pins found in '{board['name']}'.")
                return

            total = len(pins)
            output_dir = Path(self.output_var.get())
            self.after(0, self._status, f"Downloading {total} video(s) to {output_dir}…")
            done = [0]

            def cb(status: str, pin: dict, detail):
                done[0] += 1
                icons = {"ok": "✓", "skip": "–", "error": "✗"}
                msg = f"{icons[status]} {pin['pin_id']} ({done[0]}/{total})"
                pct = done[0] / total * 100
                self.after(0, lambda p=pct, m=msg: (
                    self.progress_var.set(p),
                    self.status_var.set(m),
                    self._log(m),
                ))

            ok, skip, errors = await download_all(pins, output_dir, cb)
            summary = f"Done — {ok} downloaded, {skip} skipped, {len(errors)} errors. Folder: {output_dir}"
            self.after(0, self._status, summary)
            self.after(0, self.progress_var.set, 100)
            for e in errors:
                self.after(0, self._log, f"  ERROR: {e}")

        try:
            asyncio.run(run())
        except Exception as e:
            self.after(0, self._status, f"Error: {e}")
        finally:
            self.after(0, lambda: self._dl_btn.config(state="normal"))


def run_gui():
    app = App()
    app.mainloop()
