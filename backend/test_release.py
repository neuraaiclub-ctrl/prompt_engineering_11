import os
import sys

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.database import SessionLocal, init_db
from app.models.user import User
from app.services.arena_service import ArenaService

def main():
    init_db()
    db = SessionLocal()
    
    # Get a user (admin)
    user = db.query(User).filter(User.email == "admin@neura.io").first()
    if not user:
        print("No admin user found.")
        return
        
    print(f"User: {user.email}")
    
    # Start competition to make it live
    ArenaService.start_competition(db, user, force=True)
    print("Started competition.")
    
    # Now release results
    try:
        res = ArenaService.release_results(db, user)
        print("Release results returned:", res)
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
