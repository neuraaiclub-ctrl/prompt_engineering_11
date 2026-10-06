# -*- coding: utf-8 -*-
import asyncio, aiohttp, time
from datetime import datetime

API_BASE = "https://prompt-engineering-behind.onrender.com/api/v1"
# API_BASE = "http://localhost:8000/api/v1"

WAVE_PROMPTS = [
    "Please write about marketing clearly and concisely with a good format.",
    "You are a professional marketing copywriter. Write a compelling 150-word product description for a B2B SaaS tool. Include a hook, 3 key benefits, and a CTA. Format: Intro paragraph, Bullets, CTA line.",
    "Act as a senior content strategist. Write a concise marketing brief (200 words max) for a B2B SaaS project management tool targeting mid-size engineering teams. Structure: [Hook] One surprising productivity statistic. [Value Prop] Three differentiated features with measurable outcomes. [CTA] A direct closing sentence. Tone: Professional, data-driven. Output in plain text, no markdown.",
    "You are a conversion copywriter specializing in technical B2B SaaS. Write a 180-word product marketing brief for an AI-powered project management platform targeting CTO personas at 50-500 person companies. Requirements: (1) Open with a pain-point question. (2) Present exactly 3 differentiating features each with a quantifiable outcome. (3) Close with an urgency-based CTA. Format: Plain prose, 3 short paragraphs, no bullet points. Constraints: Do not use the words revolutionary, seamless, or game-changer.",
    "System role: Award-winning B2B SaaS copywriter. Task: Draft a 200-word product brief for TaskForge. Audience: CTOs at 100-500 person companies. Paragraph 1 (40 words): Data-backed pain point. Paragraph 2 (120 words): 3 features with quantified outcomes. Paragraph 3 (40 words): CTA with social proof. Constraints: Under 200 words, plain prose only. Banned words: revolutionary, seamless, game-changer.",
]

PARTICIPANTS = [
    ("shaikhjoya702@gmail.com", "shai9395"),
    ("krutikakokate2025.ainds@mmcoe.edu.in", "krut0636"),
    ("sakshamyadav2024.it@mmcoe.edu.in", "saks1977"),
    ("kartiktikhe2025.it@mmcoe.edu.in", "kart7816"),
    ("rushikeshchadekar2025.it@mmcoe.edu.in", "rush6977"),
    ("piyushsonawane2025.ainds@mmcoe.edu.in", "piyu0358"),
    ("sahebmule7@gmail.com", "sahe6924"),
    ("sohamdegaonkar2025.it@mmcoe.edu.in", "soha8590"),
    ("atharvamangalgi2025.ainds@mmcoe.edu.in", "Atha4890"),
    ("sakshikamble2025.comp@mmcoe.edu.in", "saks9007"),
    ("vedantchandgude2026.it@mmcoe.edu.in", "veda0445"),
    ("virajtarade2024.ainds@mmcoe.edu.in", "vira3899"),
    ("mrunmayidhuldhar2025.it@mmcoe.edu.in", "mrun7616"),
    ("parthdahiphale2025.it@mmcoe.edu.in", "part9577"),
    ("aryanwaghre2025.it@mmcoe.edu.in", "arya1542"),
    ("srujanperkunde2024.ainds@mmcoe.edu.in", "sruj0595"),
    ("machalesamruddhi@gmail.com", "mach0144"),
    ("swarajkavthekar2025.etc@mmcoe.edu.in", "swar7974"),
    ("divyatakhatdeo2025.ainds@mmcoe.edu.in", "divy7640"),
    ("sanikadhore2025.ainds@mmcoe.edu.in", "sani9752"),
    ("rukminiraut444@gmail.com", "rukm4323"),
    ("tanayvidhate2025.ainds@mmcoe.edu.in", "tana7448"),
    ("sohambhopale2025.it@mmcoe.edu.in", "soha9385"),
    ("abhishekmadke2025.ainds@mmcoe.edu.in", "abhi6988"),
    ("likhitrakhade2025.comp@mmcoe.edu.in", "likh5977"),
    ("shivrajtakkalaki2025.etc@mmcoe.edu.in", "shiv0376"),
    ("abdulmerchant2025.ainds@mmcoe.edu.in", "abdu5151"),
    ("atharvaraut2025.elect@mmcoe.edu.in", "atha1577"),
    ("sarthakdeshmukh2024.ainds@mmcoe.edu.in", "sart8216"),
    ("chinmaygade2024.ainds@mmcoe.edu.in", "chin9184"),
    ("shreerajkondedeshmukh@2023.ainds@mmcoe.edu.in", "Shre9028"),
    ("yashkharabe2025.comp@mmcoe.edu.in", "yash2732"),
    ("vedantsuryawanshi2025.elect@mmcoe.edu.in", "veda3868"),
    ("abhishekgodbole2025.comp@mmcoe.edu.in", "abhi6905"),
    ("ojaskute2025.comp@mmcoe.edu.in", "ojas9041"),
    ("aparnabhamare2025.comp@mmcoe.edu.in", "apar6801"),
    ("pratikshachavan2024.comp@mmcoe.edu.in", "prat6918"),
    ("prachimorkhade07@gmail.com", "prac8578"),
    ("sammrudhikulkarni2024.comp@mmcoe.edu.in", "samm8191"),
    ("suyashkolhe2025.etc@mmcoe.edu.in", "suya6528"),
    ("vidhikabra2024.ainds@mmcoe.edu.in", "vidh8988"),
    ("yugantvarekar2024.comp@mmcoe.edu.in", "yuga9646"),
    ("shrutijadhav2025.comp@mmcoe.edu.in", "shru8057"),
    ("radhikasuryatal2024.it@mmcoe.edu.in", "radh9205"),
    ("ishakamthe2025.it@mmcoe.edu.in", "isha9527"),
    ("mrunaldoifode2025.ainds@mmcoe.edu.in", "mrun9134"),
    ("swarakulkarni2025.etc@mmcoe.edu.in", "swar1875"),
    ("atharvapardeshi992@gmail.com", "atha0668"),
    ("utkarshgedam2024.ainds@mmcoe.edu.in", "utka6916"),
    ("krishnamarne2025.ainds@mmcoe.edu.in", "kris9073"),
    ("tusharbarve2025.etc@mmcoe.edu.in", "tush1488"),
    ("sohambhoir2024.etc@mmcoe.edu.in", "soha8103"),
    ("adinathshinde2025.it@mmcoe.edu.in", "adin2058"),
    ("pritideshmukh2026.it@mmcoe.edu.in", "prit9121"),
    ("tejaswinikor2025.ainds@mmcoe.edu.in", "teja9574"),
    ("adityajathar2024.elect@mmcoe.edu.in", "adit3358"),
    ("shreyarathod2024.comp@mmcoe.edu.in", "shre9195"),
    ("shrutishelar2025.it@mmcoe.edu.in", "shru9698"),
    ("shrutimanval104@gmail.com", "shru5383"),
    ("pradeepkawade2024.it@mmcoe.edu.in", "prad5627"),
    ("sanikabobade2026.it@mmcoe.edu.in", "sani9138"),
]

results = {
    "login_ok": [], "login_fail": [],
    "challenge_ok": [], "challenge_fail": [],
    "submissions": [],
}

def log(msg):
    ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", flush=True)

async def login_user(session, email, password, retries=5):
    for attempt in range(retries):
        try:
            async with session.post(
                f"{API_BASE}/auth/login",
                json={"email": email, "password": password},
                timeout=aiohttp.ClientTimeout(total=45)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    token = data.get("access_token")
                    if token:
                        results["login_ok"].append(email)
                        return token
                text = await resp.text()
                log(f"  LOGIN FAIL [{email}]: {resp.status} - {text[:80]}")
                results["login_fail"].append(email)
                return None
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(3 + attempt * 2)  # backoff
            else:
                log(f"  LOGIN ERROR [{email}] after {retries} attempts: {type(e).__name__}")
                results["login_fail"].append(email)
                return None
    return None

async def fetch_challenge(session, email, token, retries=5):
    headers = {"Authorization": f"Bearer {token}"}
    for attempt in range(retries):
        try:
            async with session.get(
                f"{API_BASE}/arena/my-challenge",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45)
            ) as resp:
                data = await resp.json()
                if resp.status == 200:
                    if data.get("competition_status") == "waiting":
                        log(f"  CHALLENGE [{email}]: Arena is WAITING")
                        return None
                    if data.get("is_completed"):
                        log(f"  CHALLENGE [{email}]: ALREADY COMPLETED (Did you forget to RESET ARENA?)")
                        return None
                    results["challenge_ok"].append(email)
                    return data
                log(f"  CHALLENGE [{email}]: {resp.status} - {str(data)[:100]}")
                results["challenge_fail"].append(email)
                return None
        except Exception as e:
            if attempt < retries - 1:
                await asyncio.sleep(3 + attempt * 2)
            else:
                log(f"  CHALLENGE ERROR [{email}]: {type(e).__name__} {e}")
                results["challenge_fail"].append(email)
                return None
    return None

async def submit_prompt(session, email, token, wave_idx, retries=1):
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "prompt_text": WAVE_PROMPTS[wave_idx % len(WAVE_PROMPTS)],
        "diagnosis_notes": f"Load test wave {wave_idx + 1} - automated simulation"
    }
    try:
        async with session.post(
            f"{API_BASE}/arena/submit-challenge",
            json=payload,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=120)  # Increased timeout to 120s to wait in thread queue
        ) as resp:
            try:
                data = await resp.json()
            except Exception:
                data = {"raw": await resp.text()}
            
            if resp.status in (502, 503, 504):
                raise Exception(f"Server error {resp.status}")

            entry = {
                "email": email,
                "wave": wave_idx + 1,
                "status": "ok" if resp.status in (200, 201) else "fail",
                "code": resp.status,
                "msg": str(data)[:200]
            }
            results["submissions"].append(entry)
            if resp.status in (200, 201):
                log(f"  OK  W{wave_idx+1} [{email[:28]}]")
                return True
            elif resp.status == 409:
                log(f"  DUP W{wave_idx+1} [{email[:28]}]")
                return False
            elif resp.status == 403:
                log(f"  BLK W{wave_idx+1} [{email[:28]}]")
                return False
            elif resp.status == 400 and "completed all 5" in str(data):
                log(f"  FIN W{wave_idx+1} [{email[:28]}] - ALL DONE")
                return False
            elif resp.status == 400:
                log(f"  BAD W{wave_idx+1} [{email[:28]}]: {str(data)}")
                return False
            else:
                log(f"  ERR W{wave_idx+1} [{email[:28]}]: {resp.status}")
                return False
    except Exception as e:
        log(f"  NET W{wave_idx+1} [{email[:28]}]: {type(e).__name__} {e}")
        results["submissions"].append({"email": email, "wave": wave_idx+1, "status": "error", "code": 0, "msg": str(e)})
        return False

async def bounded_login(sem, session, email, password):
    async with sem:
        return await login_user(session, email, password)

async def main():
    print("=" * 65)
    print(f"  NEURA Arena - Full Lifecycle Load Test")
    print(f"  Target: {API_BASE}")
    print(f"  Participants: {len(PARTICIPANTS)}")
    print("=" * 65)
    print()
    print("INSTRUCTIONS:")
    print("  1. RESET ARENA from the Judge portal FIRST (important!)")
    print("  2. Start the Arena from the Judge portal.")
    print("  3. Watch submissions flood in on the Judge portal.")
    input("  Press ENTER when Arena is LIVE...")
    print()

    start = time.time()
    connector = aiohttp.TCPConnector(limit=250, limit_per_host=250)
    async with aiohttp.ClientSession(connector=connector) as session:
        log("Warming up Render (sending one request to wake the dyno)...")
        try:
            async with session.get(f"{API_BASE}/arena/status", timeout=aiohttp.ClientTimeout(total=30)) as r:
                log(f"Render is awake: {r.status}")
        except Exception as e:
            log(f"Warmup failed ({e}) — proceeding anyway")
        await asyncio.sleep(2)

        log(f"PHASE 1: All {len(PARTICIPANTS)} users logging in (staggered)...")
        t0 = time.time()
        
        # Stagger logins with a semaphore to prevent 502/Timeout on free dyno
        login_sem = asyncio.Semaphore(15) 
        tokens_list = await asyncio.gather(*[bounded_login(login_sem, session, e, p) for e, p in PARTICIPANTS])
        log(f"Login done {time.time()-t0:.2f}s - {len(results['login_ok'])} ok / {len(results['login_fail'])} failed")
        print()

        authenticated = {e: t for (e, _), t in zip(PARTICIPANTS, tokens_list) if t}
        if not authenticated:
            print("No users logged in. Is the backend up and running?")
            return

        log(f"PHASE 2: Synchronized Waves Load Test ({len(authenticated)} teams)")
        
        for wave_idx in range(5):
            print()
            log(f"=== WAVE {wave_idx+1} OF 5 ===")
            
            # 1. Fetch Challenge
            log(f"WAVE {wave_idx+1}: All teams fetching challenge...")
            fetch_sem = asyncio.Semaphore(30)
            async def bounded_fetch(email, token):
                async with fetch_sem:
                    return await fetch_challenge(session, email, token)
            
            t0 = time.time()
            await asyncio.gather(*[bounded_fetch(email, token) for email, token in authenticated.items()])
            log(f"WAVE {wave_idx+1}: Fetch complete in {time.time()-t0:.2f}s")
            
            await asyncio.sleep(2) # brief pause before hammering submissions
            
            # 2. Submit Challenge
            log(f"WAVE {wave_idx+1}: All teams submitting answers SIMULTANEOUSLY...")
            submit_sem = asyncio.Semaphore(100) # High concurrency to stress test DB and workers
            async def bounded_submit(email, token):
                async with submit_sem:
                    return await submit_prompt(session, email, token, wave_idx)
            
            t0 = time.time()
            await asyncio.gather(*[bounded_submit(email, token) for email, token in authenticated.items()])
            log(f"WAVE {wave_idx+1}: Submissions complete in {time.time()-t0:.2f}s")

            if wave_idx < 4:
                log(f"WAVE {wave_idx+1}: Waiting 60s for LLM processing to catch up...")
                await asyncio.sleep(60)

        log("All synchronized waves completed.")

    total = time.time() - start
    sub_ok    = [s for s in results["submissions"] if s["status"] == "ok"]
    sub_dup   = [s for s in results["submissions"] if s["code"] == 409]
    sub_block = [s for s in results["submissions"] if s["code"] == 403]
    sub_err   = [s for s in results["submissions"] if s["status"] == "error"]
    sub_hard  = [s for s in results["submissions"] if s["status"] == "fail" and s["code"] not in (409, 403)]

    print()
    print("=" * 65)
    print(f"  DONE - Total time: {total:.2f}s")
    print(f"  Login:        {len(results['login_ok'])} ok / {len(results['login_fail'])} failed")
    print(f"  Challenges:   {len(results['challenge_ok'])} ok / {len(results['challenge_fail'])} failed")
    print(f"  Submissions:  {len(results['submissions'])} total")
    print(f"    OK:         {len(sub_ok)}")
    print(f"    Duplicate:  {len(sub_dup)}")
    print(f"    Blocked:    {len(sub_block)}")
    print(f"    Hard fail:  {len(sub_hard)}")
    print(f"    Net error:  {len(sub_err)}")
    print("=" * 65)
    if results["login_fail"]:
        print("Login failures:")
        for e in results["login_fail"]:
            print(f"  - {e}")
    if sub_hard:
        print("Hard submission failures:")
        for s in sub_hard:
            print(f"  W{s['wave']} [{s['email'][:40]}]: {s['code']} {s['msg'][:80]}")

if __name__ == "__main__":
    asyncio.run(main())
