import sqlite3
import uuid

conn = sqlite3.connect('hackathon_platform.db')
cursor = conn.cursor()

# Get legacy alex user ID
cursor.execute('SELECT id FROM users WHERE email="alex@neuralninjas.io"')
u_row = cursor.fetchone()
if not u_row:
    print("User alex@neuralninjas.io not found!")
    exit(1)
u_id = u_row[0]

# Get team ID for NR-4827
cursor.execute('SELECT id FROM teams WHERE invite_code="NR-4827"')
t_row = cursor.fetchone()
if not t_row:
    print("Team NR-4827 not found!")
    exit(1)
t_id = t_row[0]

# Update team name to Neural Ninjas
cursor.execute('UPDATE teams SET name="Neural Ninjas" WHERE id=?', (t_id,))

# Check if already in team
cursor.execute('SELECT id FROM team_members WHERE user_id=?', (u_id,))
if not cursor.fetchone():
    cursor.execute('INSERT INTO team_members (id, team_id, user_id, role) VALUES (?, ?, ?, ?)', (str(uuid.uuid4()), t_id, u_id, 'leader'))
    print("Added alex@neuralninjas.io to the team.")

conn.commit()
conn.close()
print("Live DB patched.")
