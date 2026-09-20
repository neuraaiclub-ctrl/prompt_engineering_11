import asyncio
from playwright.async_api import async_playwright

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))
        print("Navigating...")
        
        await page.goto("http://localhost:5500")
        await page.evaluate("localStorage.setItem('neura_role', 'admin')")
        await page.evaluate("localStorage.setItem('neura_token', 'mock_token')")
        await page.goto("http://localhost:5500")
        
        await asyncio.sleep(5)
        await browser.close()

asyncio.run(check())
