from pathlib import Path

import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets",
]
CREDS = Credentials.from_service_account_info(
    dict(st.secrets["gcp_service_account"]), scopes=SCOPES
)


def _drive():
    return build("drive", "v3", credentials=CREDS)


def _sheets():
    return gspread.authorize(CREDS)


def subir_archivo_y_obtener_link(local_path: str, folder_id: str, publico: bool = True) -> str:
    service = _drive()
    file_metadata = {
        "name": Path(local_path).name,
        "parents": [folder_id],
    }
    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(local_path, resumable=True)

    created = (
        service.files()
        .create(
            body=file_metadata,
            media_body=media,
            fields="id, webViewLink, webContentLink",
            supportsAllDrives=True,
        )
        .execute()
    )

    file_id = created["id"]

    if publico:
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader"},
            fields="id",
            supportsAllDrives=True,
        ).execute()

        created = (
            service.files()
            .get(
                fileId=file_id,
                fields="id, webViewLink, webContentLink",
                supportsAllDrives=True,
            )
            .execute()
        )

    return created.get("webViewLink") or created.get("webContentLink")


def escribir_link_en_participantes(
    spreadsheet_id: str,
    sheet_name: str,
    documento_participante: str,
    link: str,
    columna_link: str = "archivo_doc_participante",
    columna_busqueda: str = "documento_participante",
):
    gc = _sheets()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(sheet_name)

    data = ws.get_all_records()
    df = pd.DataFrame(data)

    if columna_link not in df.columns:
        df[columna_link] = ""

    key = str(documento_participante).replace(" ", "")
    mask = df[columna_busqueda].astype(str).str.replace(r"\s+", "", regex=True).eq(key)

    if not mask.any():
        raise RuntimeError(
            f"No se encontró {columna_busqueda}={documento_participante} en {sheet_name}"
        )

    df.loc[mask, columna_link] = link

    ws.clear()
    ws.update([df.columns.tolist()] + df.fillna("").values.tolist())
