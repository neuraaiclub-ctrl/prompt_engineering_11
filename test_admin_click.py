import asyncio
from playwright.async_api import async_playwright
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        await page.goto("http://localhost:5500")
        await page.evaluate("document.getElementById('modalStaffLogin').style.display = 'flex'")
        await page.fill("#staffEmailInput", "admin1@neura.io")
        await page.fill("#staffPasswordInput", "NeuraAdmin2026!Alpha")
        await page.click("#btnPerformStaffLogin")
        await asyncio.sleep(2)
        
        # Click the button
        await page.evaluate("document.querySelector('#btnAdminStartArena').click()")
        await asyncio.sleep(2)
        
        html = await page.evaluate("document.querySelector('summary').innerHTML")
        print(f"Badge HTML after click:\n{html}")
        
        await browser.close()

asyncio.run(check())
