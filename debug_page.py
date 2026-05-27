#!/usr/bin/env python3
"""debug_page.py — dumps bounding boxes of ALL flt-semantics elements."""
from pathlib import Path
from playwright.sync_api import sync_playwright

PROFILE_DIR = str(Path(__file__).parent / "ps_profile")
URL = "https://onenv.peoplestrong.com/oneweb/#/attendance"
OUT = Path(__file__).parent / "debug_elements.txt"

with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_DIR, headless=False, args=["--no-sandbox"])
    page = context.pages[0] if context.pages else context.new_page()
    page.goto(URL, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    page.evaluate("() => { const e = document.querySelector('flt-semantics-placeholder'); if(e) e.click(); }")
    page.wait_for_timeout(3000)

    page.screenshot(path="/tmp/ps_debug.png", full_page=True)

    elements = page.evaluate("""() => {
        return [...document.querySelectorAll('flt-semantics')].map((el, i) => {
            const r = el.getBoundingClientRect();
            return {
                i,
                role: el.getAttribute('role') || '',
                label: el.getAttribute('aria-label') || '',
                x: Math.round(r.x), y: Math.round(r.y),
                w: Math.round(r.width), h: Math.round(r.height),
            };
        });
    }""")

    lines = [f"Viewport: {page.viewport_size}\n",
             f"{'#':<4} {'role':<12} {'x':<6} {'y':<6} {'w':<6} {'h':<6} label"]
    for el in elements:
        star = "⭐" if any(k in el['label'].lower() for k in ['punch','mark','entry','exit']) else "  "
        lines.append(f"{star}{el['i']:<4} {el['role']:<12} {el['x']:<6} {el['y']:<6} {el['w']:<6} {el['h']:<6} {el['label'][:60]}")

    OUT.write_text("\n".join(lines))
    print(f"✅ Saved → {OUT}\n📸 Screenshot → /tmp/ps_debug.png")
    input("Press Enter to close...")
    context.close()
