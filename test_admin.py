import asyncio
from playwright.async_api import async_playwright
import json

async def check():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: print(f"[PAGE ERROR] {err}"))
        print("Navigating to localhost:5500...")
        
        await page.goto("http://localhost:5500")
        
        # We need to simulate a login!
        # First open staff modal
        await page.evaluate("document.getElementById('modalStaffLogin').style.display = 'flex'")
        await page.fill("#staffEmailInput", "admin1@neura.io")
        await page.fill("#staffPasswordInput", "NeuraAdmin2026!Alpha")
        await page.click("#btnPerformStaffLogin")
        
        print("Waiting for login...")
        await asyncio.sleep(4)
        
        # Dump HTML of container
        html = await page.evaluate("document.getElementById('page-admin-dashboard')?.innerHTML || 'NOT_FOUND'")
        if html == 'NOT_FOUND' or not html.strip():
            print("ADMIN DASHBOARD IS BLANK OR NOT FOUND!")
        else:
            print(f"ADMIN DASHBOARD LOADED, LENGTH: {len(html)}")
            
        await browser.close()

asyncio.run(check())
