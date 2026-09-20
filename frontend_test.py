import asyncio
from playwright.async_api import async_playwright
import sys

async def check_frontend_errors():
    """
    Automated check to ensure the frontend doesn't spam unauthorized endpoints on load.
    Listens to network responses and console errors.
    """
    print("Starting Continuous Frontend Network Checker...")
    errors_found = False

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Listen for any failed network requests (401 or 403)
        page.on("response", lambda response: 
            print(f"[{response.status}] {response.url}") if response.status in [401, 403] else None
        )

        failed_responses = []
        def handle_response(response):
            if response.status in [401, 403]:
                failed_responses.append(f"{response.status} {response.url}")
        
        page.on("response", handle_response)

        # Listen for page console errors
        page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}") if msg.type == "error" else None)

        print("Navigating to http://localhost:5500 ...")
        try:
            await page.goto("http://localhost:5500", wait_until="networkidle")
        except Exception as e:
            print(f"Error connecting to frontend: {e}")
            await browser.close()
            sys.exit(1)

        # Wait a few seconds to let background intervals/renderers fire
        await asyncio.sleep(3)

        if failed_responses:
            print("\n❌ TEST FAILED: Found unauthorized network requests on idle page load:")
            for req in failed_responses:
                print(f"  - {req}")
            errors_found = True
        else:
            print("\n✅ TEST PASSED: No 401/403 network spam detected on startup.")

        await browser.close()

    if errors_found:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(check_frontend_errors())
