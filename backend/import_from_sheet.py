import urllib.request
import csv
import json
import io

url = 'https://docs.google.com/spreadsheets/d/1oe6hR236rbQl7NExUncLS1oKV7cBA8A3GoYZXDHv7FA/export?format=csv'
req = urllib.request.Request(url)
response = urllib.request.urlopen(req)
csv_data = response.read().decode('utf-8')
reader = csv.DictReader(io.StringIO(csv_data))

count = 0
headers = {
    'Content-Type': 'application/json',
    'X-Webhook-Secret': 'neura-webhook-secret-change-me'
}

for row in reader:
    email = row.get('Email address', '').strip() or row.get('Login Email', '').strip()
    if not email:
        continue
        
    print('Processing:', email)
    
    payload = {
        'login_email': email,
        'generated_password': row.get('Generated Password', '').strip(),
        'email': email,
        'phone': row.get('Mobile number', '').strip() or row.get('Contact Number', '').strip(),
        'member1_name': row.get('Name of Leader', 'Leader'),
        'member2_name': row.get('Name of member 2', ''),
        'team_name': row.get('Team Name', 'Team'),
        'department': row.get('Department', 'Dept'),
        'year': row.get('Year of study', '1st')
    }
    
    r = urllib.request.Request(
        'http://127.0.0.1:8000/api/v1/webhook/form-submission',
        data=json.dumps(payload).encode(),
        headers=headers,
        method='POST'
    )
    
    try:
        res = urllib.request.urlopen(r)
        count += 1
        print('Pushed row', count)
    except Exception as e:
        print('Error pushing:', e)

print('Total pushed:', count)
