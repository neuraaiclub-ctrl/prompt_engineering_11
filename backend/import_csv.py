import csv
import json
import urllib.request
import urllib.error

headers = {
    'Content-Type': 'application/json',
    'X-Webhook-Secret': 'neura-webhook-secret-change-me'
}

with open('responses.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    count = 0
    for row in reader:
        email = row.get('Email Address', '').strip()
        if not email:
            continue
            
        print(f"Processing: {email}")
        
        payload = {
            'login_email': row.get('Login Email', '').strip() or email,
            'generated_password': row.get('Generated Password', '').strip(),
            'email': email,
            'phone': row.get('Mobile Number', '').strip().replace('+91', '').replace(' ', ''),
            'member1_name': row.get('Member 1 Name (Team Leader)', '').strip() or 'Leader',
            'member2_name': row.get('Member 2 Name (Optional)', '').strip(),
            'team_name': row.get('Team Name', '').strip() or 'Team',
            'department': row.get('Department / Branch', '').strip() or 'Dept',
            'year': row.get('Year of Study', '').strip() or '1st Year'
        }
        
        req = urllib.request.Request(
            'http://127.0.0.1:8000/api/v1/webhook/form-submission',
            data=json.dumps(payload).encode('utf-8'),
            headers=headers,
            method='POST'
        )
        
        try:
            res = urllib.request.urlopen(req)
            count += 1
            print(f"Successfully pushed: {email}")
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8')
            print(f"Failed to push {email}: {e.code} - {err_body}")
        except Exception as e:
            print(f"Failed to push {email}: {str(e)}")

print(f"\nTotal records imported successfully into Supabase: {count}")
