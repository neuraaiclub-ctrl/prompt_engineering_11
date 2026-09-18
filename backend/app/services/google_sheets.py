import os
import json
from typing import List, Dict, Any, Optional
from app.config import settings

class GoogleSheetsService:
    @staticmethod
    def is_configured() -> bool:
        if not settings.GOOGLE_SHEETS_ENABLED:
            return False
        if not settings.GOOGLE_SHEET_ID:
            return False
        if settings.GOOGLE_SERVICE_ACCOUNT_JSON or (settings.GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE)):
            return True
        return False

    @classmethod
    def fetch_sheet_rows(cls) -> List[Dict[str, Any]]:
        """
        Connects to Google Sheets API using Google Service Account credentials.
        Returns a list of dicts mapping column headers to row cell values.
        """
        if not cls.is_configured():
            raise ValueError("Google Sheets API integration is not fully configured or enabled.")

        try:
            from google.oauth2 import service_account
            from googleapiclient.discovery import build
        except ImportError:
            raise ImportError("Google Client library (google-api-python-client, google-auth) is not installed.")

        scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        creds = None

        if settings.GOOGLE_SERVICE_ACCOUNT_JSON:
            try:
                info = json.loads(settings.GOOGLE_SERVICE_ACCOUNT_JSON)
                creds = service_account.Credentials.from_service_account_info(info, scopes=scopes)
            except Exception as e:
                raise ValueError(f"Failed to parse GOOGLE_SERVICE_ACCOUNT_JSON: {str(e)}")
        elif settings.GOOGLE_SERVICE_ACCOUNT_FILE and os.path.exists(settings.GOOGLE_SERVICE_ACCOUNT_FILE):
            creds = service_account.Credentials.from_service_account_file(
                settings.GOOGLE_SERVICE_ACCOUNT_FILE, scopes=scopes
            )
        else:
            raise ValueError("No valid Google service account credentials provided.")

        service = build('sheets', 'v4', credentials=creds)
        sheet_range = f"{settings.GOOGLE_SHEET_NAME}!{settings.GOOGLE_SHEET_RANGE}" if settings.GOOGLE_SHEET_NAME else settings.GOOGLE_SHEET_RANGE

        result = service.spreadsheets().values().get(
            spreadsheetId=settings.GOOGLE_SHEET_ID,
            range=sheet_range
        ).execute()

        values = result.get('values', [])
        if not values or len(values) < 2:
            return []

        headers = [str(h).strip() for h in values[0]]
        rows = []

        for row_idx, row_values in enumerate(values[1:], start=2):
            row_dict = {"_source_row": row_idx}
            for col_idx, header in enumerate(headers):
                val = row_values[col_idx] if col_idx < len(row_values) else ""
                row_dict[header] = str(val).strip()
            rows.append(row_dict)

        return rows
