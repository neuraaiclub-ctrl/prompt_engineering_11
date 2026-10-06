import asyncio
import aiohttp
import sqlite3
import time

# Update these URLs to target your live environment or local server
API_BASE = "https://prompt-engineering-behind.onrender.com/api/v1"
# API_BASE = "http://localhost:8000/api/v1"

async def login_and_submit(session, email, password):
    # 1. Login
    login_data = {"email": email, "password": password}
    try:
        async with session.post(f"{API_BASE}/auth/login", json=login_data) as resp:
            if resp.status != 200:
                print(f"[{email}] Login failed: {resp.status}")
                return False
            
            data = await resp.json()
            token = data.get("access_token")
            if not token:
                print(f"[{email}] No token returned")
                return False
    except Exception as e:
        print(f"[{email}] Connection error during login: {e}")
        return False
        
    print(f"[{email}] Logged in successfully!")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Submit to Arena
    # This assumes the arena is active for the user
    payload = {
        "submitted_prompt": f"This is a load-tested automated prompt submission for {email}",
        "time_taken_seconds": 120
    }
    
    try:
        async with session.post(f"{API_BASE}/arena/submit", json=payload, headers=headers) as resp:
            resp_data = await resp.json()
            if resp.status in [200, 201]:
                print(f"[{email}] ✅ Submission SUCCESS!")
                return True
            else:
                print(f"[{email}] ❌ Submission FAILED: {resp.status} - {resp_data}")
                return False
    except Exception as e:
        print(f"[{email}] Connection error during submission: {e}")
        return False

async def main():
    # 1. Fetch all participant emails from the local SQLite DB
    # Note: If your production uses a different password for each team, 
    # you'll need those passwords. Assuming 'Pass123!' or similar for load tests.
    db_path = "backend/app/hackathon_platform.db" # adjust path if needed
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # We find all users who have the 'participant' role
        # Depending on your schema, it might be easier to just query users
        cursor.execute("SELECT email FROM users WHERE roles LIKE '%participant%'")
        users = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"Database error: {e}")
        return
        
    emails = [u[0] for u in users]
    
    if not emails:
        print("No participants found in database.")
        return
        
    print(f"Found {len(emails)} participants. Starting load test in 3 seconds...")
    time.sleep(3)
    
    # IMPORTANT: What is the default password for your teams? 
    # Change this if they don't use 'Pass123!'
    COMMON_PASSWORD = "Pass123!" 
    
    async with aiohttp.ClientSession() as session:
        # Create a task for every single team
        tasks = [login_and_submit(session, email, COMMON_PASSWORD) for email in emails]
        
        print(f"Firing {len(tasks)} simultaneous login & submission requests...")
        
        # Fire them all simultaneously
        start_time = time.time()
        results = await asyncio.gather(*tasks)
        end_time = time.time()
        
        successes = sum(1 for r in results if r)
        print(f"\n--- Load Test Complete ---")
        print(f"Total time: {end_time - start_time:.2f} seconds")
        print(f"Successful submissions: {successes} / {len(tasks)}")

if __name__ == "__main__":
    asyncio.run(main())
