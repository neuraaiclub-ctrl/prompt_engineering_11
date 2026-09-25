import asyncio
import json
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        
        pages_to_test = [
            'http://127.0.0.1:5500/index.html',
            'http://127.0.0.1:5500/arena.html',
            'http://127.0.0.1:5500/admin.html',
            'http://127.0.0.1:5500/judge.html',
            'http://127.0.0.1:5500/live.html',
            'http://127.0.0.1:5500/team.html',
            'http://127.0.0.1:5500/login.html'
        ]
        
        all_errors = {}
        
        for url in pages_to_test:
            page = await browser.new_page()
            errors = []
            page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else None)
            page.on('pageerror', lambda exc: errors.append(str(exc)))
            
            try:
                await page.goto(url)
                await asyncio.sleep(2)
            except Exception as e:
                errors.append(str(e))
                
            all_errors[url] = errors
            await page.close()
            
        print(json.dumps(all_errors, indent=2))
        await browser.close()

if __name__ == '__main__':
    asyncio.run(run())
