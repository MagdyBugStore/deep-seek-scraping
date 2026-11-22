"""DeepSeek chat scraper: many parallel chats, each with its own prompt list."""
from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.async_api import BrowserContext, Page, async_playwright
from playwright.async_api import TimeoutError as PWTimeout

URL = "https://chat.deepseek.com/"

# Selectors live in one place: DeepSeek changes its DOM sometimes.
SEL_INPUT = "textarea#chat-input, textarea[placeholder*='DeepSeek'], textarea"
SEL_ANSWER = ".ds-markdown"


@dataclass
class ChatJob:
    name: str
    prompts: list[str]
    deepthink: bool | None = None  # None = leave site default
    search: bool | None = None


@dataclass
class Options:
    profile_dir: Path = Path(".profile")
    out_dir: Path = Path("results")
    headless: bool = False
    channel: str | None = None  # e.g. "chrome" to use installed Chrome
    concurrency: int = 3
    stagger: float = 2.0  # seconds between starting chats
    timeout: float = 180.0  # max seconds per answer
    stable: float = 3.0  # answer text unchanged this long = done
    retries: int = 1
    cdp: str | None = None  # attach to a running real Chrome, e.g. http://localhost:9222
    log: Callable[[str], None] = print


CDP_PORT = 9222
CHROME_PATHS = [
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    str(Path.home() / r"AppData\Local\Google\Chrome\Application\chrome.exe"),
]


def launch_real_chrome(profile_dir: Path, port: int = CDP_PORT) -> None:
    """Start the user's real Chrome (no automation flags) with a debug port."""
    import subprocess

    exe = next((p for p in CHROME_PATHS if Path(p).exists()), None)
    if not exe:
        raise RuntimeError("chrome.exe not found; edit CHROME_PATHS in scraper.py")
    subprocess.Popen(
        [exe, f"--remote-debugging-port={port}",
         f"--user-data-dir={profile_dir.resolve()}", URL],
        creationflags=0x00000008,  # DETACHED_PROCESS: survives this CLI exiting
    )


def _launch_kwargs(o: Options, headless: bool) -> dict:
    kw = dict(
        user_data_dir=str(o.profile_dir),
        headless=headless,
        viewport={"width": 1280, "height": 900},
        args=["--disable-blink-features=AutomationControlled"],
        # hides "controlled by automation" flag; helps Google sign-in accept the browser
        ignore_default_args=["--enable-automation"],
    )
    if o.channel:
        kw["channel"] = o.channel
    return kw


async def login(o: Options) -> None:
    """Open headed browser so user logs in once; session saved in profile dir."""
    async with async_playwright() as pw:
        ctx = await pw.chromium.launch_persistent_context(**_launch_kwargs(o, False))
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        await page.goto(URL)
        o.log("Log in to DeepSeek in the browser window, then press Enter here.")
        await asyncio.get_running_loop().run_in_executor(None, input)
        await ctx.close()
    o.log(f"Session saved in {o.profile_dir}")


async def _toggle(page: Page, label: str, want: bool | None) -> None:
    """Best-effort toggle for DeepThink / Search buttons."""
    if want is None:
        return
    btn = page.locator(f"div[role='button']:has-text('{label}')").first
    try:
        if await btn.count() == 0:
            return
        cls = await btn.get_attribute("class") or ""
        on = "selected" in cls or "ds-toggle-button--selected" in cls
        if on != want:
            await btn.click()
    except Exception:
        pass


async def _wait_ready(page: Page) -> None:
    try:
        await page.wait_for_selector(SEL_INPUT, timeout=30_000)
    except PWTimeout:
        raise RuntimeError(
            "Chat input not found. Not logged in? Run `login` first (or Cloudflare challenge)."
        )


async def _ask(page: Page, prompt: str, o: Options) -> str:
    before = await page.locator(SEL_ANSWER).count()
    box = page.locator(SEL_INPUT).first
    await box.click()
    await box.fill(prompt)
    await box.press("Enter")

    deadline = time.monotonic() + o.timeout
    # wait for new answer block to appear
    while await page.locator(SEL_ANSWER).count() <= before:
        if time.monotonic() > deadline:
            raise TimeoutError("no answer started")
        await asyncio.sleep(0.5)

    # wait until text stops changing
    last, last_change = "", time.monotonic()
    while True:
        cur = await page.locator(SEL_ANSWER).last.inner_text()
        now = time.monotonic()
        if cur != last:
            last, last_change = cur, now
        elif cur.strip() and now - last_change >= o.stable:
            return cur
        if now > deadline:
            if last.strip():
                return last  # partial, better than nothing
            raise TimeoutError("answer timeout")
        await asyncio.sleep(0.5)


async def _run_chat(ctx: BrowserContext, job: ChatJob, o: Options,
                    sem: asyncio.Semaphore, delay: float, sink: Path) -> list[dict]:
    await asyncio.sleep(delay)
    results: list[dict] = []
    async with sem:
        page = await ctx.new_page()
        try:
            await page.goto(URL)
            await _wait_ready(page)
            await _toggle(page, "DeepThink", job.deepthink)
            await _toggle(page, "Search", job.search)
            for i, prompt in enumerate(job.prompts, 1):
                rec = {"chat": job.name, "index": i, "prompt": prompt,
                       "answer": None, "error": None,
                       "time": datetime.now().isoformat(timespec="seconds")}
                for attempt in range(o.retries + 1):
                    try:
                        rec["answer"] = await _ask(page, prompt, o)
                        rec["error"] = None
                        break
                    except Exception as e:  # noqa: BLE001
                        rec["error"] = f"{type(e).__name__}: {e}"
                        o.log(f"[{job.name}] prompt {i} attempt {attempt + 1} failed: {rec['error']}")
                results.append(rec)
                with sink.open("a", encoding="utf-8") as f:
                    f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                status = "ok" if rec["answer"] else "FAILED"
                o.log(f"[{job.name}] {i}/{len(job.prompts)} {status}")
        except Exception as e:  # noqa: BLE001
            o.log(f"[{job.name}] chat aborted: {e}")
            if not results:
                results.append({"chat": job.name, "index": 0, "prompt": None,
                                "answer": None, "error": str(e)})
        finally:
            await page.close()
    return results


async def run(jobs: list[ChatJob], o: Options) -> Path:
    run_dir = o.out_dir / datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir.mkdir(parents=True, exist_ok=True)
    sink = run_dir / "results.jsonl"
    sem = asyncio.Semaphore(max(1, o.concurrency))

    async with async_playwright() as pw:
        if o.cdp:
            browser = await pw.chromium.connect_over_cdp(o.cdp)
            ctx = browser.contexts[0]
        else:
            ctx = await pw.chromium.launch_persistent_context(**_launch_kwargs(o, o.headless))
        try:
            tasks = [
                _run_chat(ctx, j, o, sem, idx * o.stagger, sink)
                for idx, j in enumerate(jobs)
            ]
            all_res = await asyncio.gather(*tasks)
        finally:
            if o.cdp:
                await browser.close()  # only drops our CDP link; Chrome keeps running
            else:
                await ctx.close()

    # per-chat json + markdown for easy reading
    for job, res in zip(jobs, all_res):
        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in job.name)
        (run_dir / f"{safe}.json").write_text(
            json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
        md = [f"# {job.name}\n"]
        for r in res:
            md.append(f"## {r['index']}. {r['prompt']}\n\n{r['answer'] or '_' + str(r['error']) + '_'}\n")
        (run_dir / f"{safe}.md").write_text("\n".join(md), encoding="utf-8")
    return run_dir
