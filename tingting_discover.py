"""Inspect TingtingFM program pages to discover public episode APIs.

This diagnostic does not download or redistribute audio. It redacts likely
credentials and strips URL query parameters from recorded requests.
"""
import asyncio
import json
import re
from pathlib import Path
from urllib.parse import urlsplit
from playwright.async_api import async_playwright

PROGRAMS = {
    "science": "https://mobile.tingtingfm.com/v3/program/OjdkYXRaBm",
    "other": "https://mobile.tingtingfm.com/v3/program/ZXJQ5r3JN0",
}
OUTPUT = Path("tingting-diagnostics")
OUTPUT.mkdir(exist_ok=True)
SENSITIVE = re.compile(r"token|secret|auth|sign|cookie|password|key|session|credential", re.I)


def safe_url(url):
    parsed = urlsplit(url)
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def scrub(value, depth=0):
    if depth > 5:
        return "[nested data]"
    if isinstance(value, dict):
        return {str(k): ("[redacted]" if SENSITIVE.search(str(k)) else scrub(v, depth + 1))
                for k, v in list(value.items())[:35]}
    if isinstance(value, list):
        return {"count": len(value), "sample": [scrub(v, depth + 1) for v in value[:3]]}
    if isinstance(value, str):
        return safe_url(value) if value.startswith(("http://", "https://")) else value[:180]
    return value


async def inspect(browser, name, url):
    context = await browser.new_context(locale="zh-CN", viewport={"width": 1280, "height": 900})
    page = await context.new_page()
    calls = []
    tasks = []

    async def capture(response):
        if "tingtingfm.com" not in response.url or len(calls) >= 120:
            return
        if not any(x in response.url for x in ("/api", "albumaudio", "album", "audio", "list")):
            return
        entry = {"url": safe_url(response.url), "status": response.status}
        try:
            if "json" in response.headers.get("content-type", ""):
                entry["response_shape"] = scrub(await response.json())
        except Exception as exc:
            entry["error"] = type(exc).__name__
        calls.append(entry)

    page.on("response", lambda response: tasks.append(asyncio.create_task(capture(response))))
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await page.wait_for_timeout(12000)
        for _ in range(5):
            await page.mouse.wheel(0, 1100)
            await page.wait_for_timeout(1500)
        result = {"source": url, "title": await page.title(),
                  "page_excerpt": (await page.locator("body").inner_text(timeout=10000))[:2500]}
    except Exception as exc:
        result = {"source": url, "error": str(exc)[:300]}
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
    result["api_responses"] = calls
    (OUTPUT / f"{name}.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{name}: recorded {len(calls)} responses", flush=True)
    await context.close()


async def main():
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        for name, url in PROGRAMS.items():
            await inspect(browser, name, url)
        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
