import asyncio
from playwright.async_api import async_playwright
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

errors = []

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: errors.append(f"[{msg.type.upper()}] {msg.text}") if msg.type in ('error','warning') else None)
        page.on("pageerror", lambda err: errors.append(f"[PAGEERROR] {err}"))

        await page.goto("http://localhost:5500")
        await asyncio.sleep(1)

        # Log in as participant
        await page.evaluate("document.getElementById('modalStaffLogin').style.display = 'none'")
        btn = await page.query_selector('#btnNavSignIn')
        if btn:
            await btn.click()
            await asyncio.sleep(1)

        # Use staff login for participant (bypass nav)
        await page.evaluate("document.getElementById('modalStaffLogin').style.display = 'flex'")
        await page.fill('#staffEmailInput', 'alex.mercer@neura.io')
        await page.fill('#staffPasswordInput', 'Pass123!')
        await page.click('#btnPerformStaffLogin')
        await asyncio.sleep(3)

        active = await page.evaluate("document.querySelector('.view-section.active')?.id")
        print(f"Active section after login: {active}")

        # Check for console errors
        print(f"\nErrors/Warnings ({len(errors)}):")
        for e in errors:
            print(e)

        await browser.close()

asyncio.run(check())
