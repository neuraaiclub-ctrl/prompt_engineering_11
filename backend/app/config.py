import os

class Settings:
    PROJECT_NAME: str = "Prompt Engineering Hackathon Platform"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str = os.getenv("SECRET_KEY", "neura_hackathon_super_secret_jwt_key_2026_x894")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day for dev/hackathon convenience
    
    # SQLite default database path (upgradeable to PostgreSQL via env)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./hackathon_platform.db")

    # Security & CORS configuration
    cors_env = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: list = [origin.strip() for origin in cors_env.split(",") if origin.strip()] if cors_env else [
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8000",
        "http://localhost:8000"
    ]
    MAX_REQUEST_SIZE_BYTES: int = int(os.getenv("MAX_REQUEST_SIZE_BYTES", str(2 * 1024 * 1024))) # 2 MB max body size

    # Seed Admin Accounts (3 Separate Administrator Credentials)
    ADMIN1_EMAIL: str = os.getenv("ADMIN1_EMAIL", "admin1@neura.io")
    ADMIN1_PASSWORD: str = os.getenv("ADMIN1_PASSWORD", "NeuraAdmin2026!Alpha")
    ADMIN1_NAME: str = os.getenv("ADMIN1_NAME", "Director Vance (Admin 1)")

    ADMIN2_EMAIL: str = os.getenv("ADMIN2_EMAIL", "admin2@neura.io")
    ADMIN2_PASSWORD: str = os.getenv("ADMIN2_PASSWORD", "NeuraAdmin2026!Beta")
    ADMIN2_NAME: str = os.getenv("ADMIN2_NAME", "Lead Organizer (Admin 2)")

    ADMIN3_EMAIL: str = os.getenv("ADMIN3_EMAIL", "admin3@neura.io")
    ADMIN3_PASSWORD: str = os.getenv("ADMIN3_PASSWORD", "NeuraAdmin2026!Gamma")
    ADMIN3_NAME: str = os.getenv("ADMIN3_NAME", "System Supervisor (Admin 3)")

    # Seed Judge Account
    JUDGE1_EMAIL: str = os.getenv("JUDGE1_EMAIL", "judge1@neura.io")
    JUDGE1_PASSWORD: str = os.getenv("JUDGE1_PASSWORD", "NeuraJudge2026!Eval")
    JUDGE1_NAME: str = os.getenv("JUDGE1_NAME", "Dr. Vance (Judge)")

    # Google Sheets Live Registration Sync Configuration
    GOOGLE_SHEETS_ENABLED: bool = os.getenv("GOOGLE_SHEETS_ENABLED", "false").lower() == "true"
    GOOGLE_SHEET_ID: str = os.getenv("GOOGLE_SHEET_ID", "")
    GOOGLE_SHEET_NAME: str = os.getenv("GOOGLE_SHEET_NAME", "Form Responses 1")
    GOOGLE_SHEET_RANGE: str = os.getenv("GOOGLE_SHEET_RANGE", "A:Z")
    GOOGLE_SERVICE_ACCOUNT_FILE: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "")
    GOOGLE_SERVICE_ACCOUNT_JSON: str = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")

    REGISTRATION_SYNC_ENABLED: bool = os.getenv("REGISTRATION_SYNC_ENABLED", "false").lower() == "true"
    REGISTRATION_SYNC_INTERVAL_SECONDS: int = int(os.getenv("REGISTRATION_SYNC_INTERVAL_SECONDS", "300"))

    # Configurable Registration Column Mapping
    REGISTRATION_COLUMN_MAP: dict = {
        "Timestamp": "submitted_at",
        "Registration ID": "external_registration_id",
        "Team Name": "team_name",
        "Participant Name": "participant_name",
        "Email": "email",
        "Phone": "phone",
        "College": "college",
        "Course": "course",
        "Year": "year",
        "Member 1 Name": "member_1_name",
        "Member 1 Email": "member_1_email",
        "Member 2 Name": "member_2_name",
        "Member 2 Email": "member_2_email",
        "Member 3 Name": "member_3_name",
        "Member 3 Email": "member_3_email",
        "Member 4 Name": "member_4_name",
        "Member 4 Email": "member_4_email",
    }

settings = Settings()

