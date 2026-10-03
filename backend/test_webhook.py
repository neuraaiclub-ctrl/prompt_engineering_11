from dotenv import load_dotenv
load_dotenv('.env')

from app.database import SessionLocal
from app.api.webhook import handle_form_submission, FormSubmissionPayload

db = SessionLocal()
try:
    payload = FormSubmissionPayload(
        login_email="test2@example.com",
        generated_password="pwd",
        team_name="Test2",
        member1_name="Test2",
        email="test2@example.com"
    )
    result = handle_form_submission(payload=payload, db=db, _=None)
    print("SUCCESS:", result)
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
