from __future__ import annotations

import asyncio
import json
from pathlib import Path

import click

from .scraper import CDP_PORT, ChatJob, Options, launch_real_chrome, login as do_login, run as do_run


def _load_jobs(path: Path) -> list[ChatJob]:
    data = json.loads(path.read_text(encoding="utf-8"))
    chats = data["chats"] if isinstance(data, dict) else data
    jobs = []
    for i, c in enumerate(chats, 1):
        jobs.append(ChatJob(
            name=c.get("name", f"chat{i}"),
            prompts=list(c["prompts"]),
            deepthink=c.get("deepthink"),
            search=c.get("search"),
        ))
    return jobs


def _opts(profile, out, headless, channel, concurrency, stagger, timeout, stable, retries,
          real_chrome=False) -> Options:
    return Options(profile_dir=Path(profile), out_dir=Path(out), headless=headless,
                   channel=channel, concurrency=concurrency, stagger=stagger,
                   timeout=timeout, stable=stable, retries=retries,
                   cdp=f"http://localhost:{CDP_PORT}" if real_chrome else None)


real_chrome_opt = click.option("--real-chrome", is_flag=True,
                               help="Attach to Chrome started by `dschat chrome` (recommended).")

common = [
    click.option("--profile", default=".profile", show_default=True, help="Browser profile dir (keeps login)."),
    click.option("--channel", default=None, help="Use installed browser, e.g. 'chrome' or 'msedge'."),
]


def add(opts):
    def deco(f):
        for o in reversed(opts):
            f = o(f)
        return f
    return deco


@click.group()
def main():
    """Drive many DeepSeek chats in parallel, each with a list of prompts."""


@main.command()
@add(common)
def login(profile, channel):
    """Open browser once to log in. Session is saved in the profile."""
    o = Options(profile_dir=Path(profile), channel=channel)
    asyncio.run(do_login(o))


@main.command()
@click.option("--profile", default=".chrome-profile", show_default=True)
def chrome(profile):
    """Start real Chrome with a debug port. Log in with Google there once, keep it open."""
    launch_real_chrome(Path(profile))
    click.echo("Chrome started. Log in to DeepSeek (Google) if needed, leave the window open,\n"
               "then: python -m dschat run FILE --real-chrome")


@main.command()
@real_chrome_opt
@click.argument("config", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--out", default="results", show_default=True, help="Output dir.")
@click.option("-n", "--concurrency", default=3, show_default=True, help="Max chats open at once.")
@click.option("--headless/--headed", default=False, show_default=True)
@click.option("--stagger", default=2.0, show_default=True, help="Seconds between chat starts.")
@click.option("--timeout", default=180.0, show_default=True, help="Max seconds per answer.")
@click.option("--stable", default=3.0, show_default=True, help="Seconds of unchanged text = answer done.")
@click.option("--retries", default=1, show_default=True)
@add(common)
def run(real_chrome, config, out, concurrency, headless, stagger, timeout, stable, retries, profile, channel):
    """Run chats defined in CONFIG (JSON). See prompts.example.json."""
    jobs = _load_jobs(config)
    o = _opts(profile, out, headless, channel, concurrency, stagger, timeout, stable, retries, real_chrome)
    run_dir = asyncio.run(do_run(jobs, o))
    click.echo(f"Done. Results in {run_dir}")


@main.command()
@real_chrome_opt
@click.option("-p", "--prompt", "prompts", multiple=True, required=True, help="Prompt (repeat for many).")
@click.option("--out", default="results", show_default=True)
@click.option("--headless/--headed", default=False, show_default=True)
@click.option("--timeout", default=180.0, show_default=True)
@click.option("--stable", default=3.0, show_default=True)
@add(common)
def ask(real_chrome, prompts, out, headless, timeout, stable, profile, channel):
    """Quick single chat: ask -p "q1" -p "q2"."""
    jobs = [ChatJob(name="chat1", prompts=list(prompts))]
    o = _opts(profile, out, headless, channel, 1, 0, timeout, stable, 1, real_chrome)
    run_dir = asyncio.run(do_run(jobs, o))
    click.echo((run_dir / "chat1.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
