import asyncio
from pathlib import Path

import click


@click.command()
@click.option("--no-gui", is_flag=True, help="Run in terminal (no GUI window)")
@click.option("--url", "-u", default=None, help="Pinterest board URL")
@click.option("--output", "-o", default="./pinterest_downloads", show_default=True, help="Output directory")
@click.option("--cookie", default=None, help="Raw cookie string (overrides browser auto-detect)")
def main(no_gui: bool, url: str | None, output: str, cookie: str | None):
    if no_gui:
        _run_cli(url, output, cookie)
    else:
        from gui import run_gui
        run_gui()


def _run_cli(url: str | None, output: str, cookie: str | None):
    from rich.console import Console

    from auth import get_cookies_auto, parse_cookie_string
    from client import get_board, iter_board_video_pins, parse_board_url
    from downloader import download_all

    console = Console()

    if not url:
        url = console.input("[bold]Board URL:[/bold] ").strip()

    async def run():
        try:
            username, slug = parse_board_url(url)
            cookies = parse_cookie_string(cookie) if cookie else get_cookies_auto()
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            return

        with console.status(f"Fetching board pinterest.com/{username}/{slug}/…"):
            board = await get_board(username, slug, cookies)
        console.print(f"Board: [bold]{board['name']}[/bold]. Scanning for video pins…")

        pins: list[dict] = []
        async for pin in iter_board_video_pins(board["id"], board["name"], username, cookies):
            pins.append(pin)
            console.print(f"  found {len(pins)} video pin(s)…", end="\r")

        if not pins:
            console.print("[yellow]No video pins found.[/yellow]")
            return

        total = len(pins)
        console.print(f"\n[green]{total}[/green] video pin(s) found → downloading to [bold]{output}[/bold]")
        output_dir = Path(output)
        done = [0]

        def progress_cb(status: str, pin: dict, detail):
            done[0] += 1
            icon = {"ok": "[green]✓[/green]", "skip": "[dim]–[/dim]", "error": "[red]✗[/red]"}[status]
            console.print(f"  {icon} {pin['pin_id']} ({done[0]}/{total})")

        ok, skip, errors = await download_all(pins, output_dir, progress_cb)
        console.print(f"\n[bold green]Done:[/bold green] {ok} downloaded, {skip} skipped, {len(errors)} errors")
        for e in errors:
            console.print(f"  [red]✗[/red] {e}")

    asyncio.run(run())


if __name__ == "__main__":
    main()
