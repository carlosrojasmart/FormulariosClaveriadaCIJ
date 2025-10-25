from pathlib import Path
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import streamlit as st

SCOPES = ["https://www.googleapis.com/auth/drive"]
CREDS = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=SCOPES)
drive = build("drive", "v3", credentials=CREDS)

def upload_file_to_drive(local_path: str, folder_id: str, publico=True) -> str:
    file_metadata = {"name": Path(local_path).name, "parents": [folder_id]}
    created = drive.files().create(
        body=file_metadata,
        media_body=MediaFileUpload(local_path, resumable=True),
        fields="id, webViewLink, webContentLink",
        supportsAllDrives=True,   
    ).execute()

    file_id = created["id"]

    if publico:
        drive.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
            supportsAllDrives=True,
        ).execute()

        created = drive.files().get(
            fileId=file_id, fields="id, webViewLink, webContentLink", supportsAllDrives=True
        ).execute()

    return created.get("webViewLink") or created.get("webContentLink")
