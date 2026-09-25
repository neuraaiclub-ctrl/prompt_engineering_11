import sys, os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from app.database import SessionLocal
from app.models.user import User
from app.core.security import verify_password

db = SessionLocal()
email = 'alex@neuralninjas.io'
user = db.query(User).filter(User.email == email).first()
print(f'User found: {user is not None}')
if user:
    print(f'Password OK: {verify_password("password123", user.password_hash)}')
    print(f'Status: {user.status}')
else:
    print('User is None')
