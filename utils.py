from typing import List
import re
import textwrap
import json
import mimetypes
from pathlib import Path
from contextlib import suppress

import gspread
import pandas as pd
import streamlit as st
from gspread.exceptions import WorksheetNotFound
from google.oauth2.service_account import Credentials
from google.auth.transport.requests import AuthorizedSession

EXPERIENCIAS_PARTICIPANTE = [
    ("Misión de servicio", "exp_mision_servicio_rank"),
    ("Peregrinar con sentido", "exp_peregrinar_sentido_rank"),
    ("Incidencia política ignaciana", "exp_incidencia_politica_ignaciana_rank"),
    ("Espiritualidad y vida interior", "exp_espiritualidad_vida_interior_rank"),
    ("Curiosidad a la vida religiosa", "exp_curiosidad_vida_religiosa_rank"),
    ("Arte, cultura y comunicación", "exp_arte_cultura_comunicacion_rank"),
    ("Reconciliación ecológica", "exp_reconciliacion_ecologica_rank"),
]

EXPERIENCIAS_PARTICIPANTE_LABELS = tuple(label for label, _ in EXPERIENCIAS_PARTICIPANTE)
EXPERIENCIAS_PARTICIPANTE_COLUMNS = tuple(column for _, column in EXPERIENCIAS_PARTICIPANTE)

PARTICIPANTES_COLS = [
    "timestamp","es_mayor_edad","tipo_documento_participante","documento_participante","nombres","apellidos",
    "nombre_completo","como_te_gusta_que_te_digan","telefono_celular","correo","direccion","region","ciudad",
    "fecha_nacimiento","edad_aprox","talla_camisa","eps","restricciones_alimentarias","salud_mental",
    "obra_institucion","proceso_juvenil","intereses_personales","experiencia_significativa",
    "hobby_o_dato_curioso","pregunta_para_conectar",
    *EXPERIENCIAS_PARTICIPANTE_COLUMNS,
    "experiencia_top_calculada","nivel_experticie","motivo_experiencia_top","preguntas_frecuentes",
    "acompanamientos_marcados","acompanamiento_familia","acompanamiento_amigos","acompanamiento_escucha_activa",
    "acompanamiento_mentoria","acompanamiento_espiritual","acompanamiento_red_comunitaria","acompanamiento_ninguna",
    "conoce_rji","tipo_documento_contacto","documento_contacto","nombres_contacto","apellidos_contacto","telefono_contacto",
    "correo_contacto","parentesco_contacto","archivo_doc_participante",
    "acepta_tratamiento_datos","acepta_whatsapp"
]

ACOMPANANTES_COLS = [
    "timestamp","tipo_documento_acompanante","documento_acompanante","nombre_acompanante","correo_acompanante",
    "telefono_acompanante","organizacion","region","rol_en_organizacion","delegacion_que_acompana",
    "tamano_delegacion","medio_de_viaje","trae_varios_jovenes","experiencias_niveladas",
    "ciudad_origen","hora_llegada_medellin",
    "archivo_lista_menores_url","lista_documentos_menores_texto"
]

UNIFICADO_COLS = [
    "documento_participante","nombre_completo","es_mayor_edad","documento_acudiente_declarado","match_acudiente_en_form",
    "documento_acompanante_real","nombre_acompanante_real","tiene_archivo_consentimiento",
    "consentimiento_lista_contiene_doc_participante","observaciones"
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]


def _normalize_private_key(info: dict) -> dict:
    """Devuelve una copia del diccionario con la clave privada formateada correctamente."""
    cleaned = dict(info) if info is not None else {}
    private_key = cleaned.get("private_key")
    if not isinstance(private_key, str):
        return cleaned

    raw = private_key.strip().strip("\"'")
    raw = raw.replace("\r", "\n")
    raw = raw.replace("\\r", "\n").replace("\\n", "\n")
    try:
        raw = raw.encode("utf-8").decode("unicode_escape")
    except UnicodeDecodeError:
        pass

    if "BEGIN PRIVATE KEY" not in raw or "END PRIVATE KEY" not in raw:
        cleaned["private_key"] = raw
        return cleaned

    match = re.search(r"-----BEGIN PRIVATE KEY-----\s*(.*?)\s*-----END PRIVATE KEY-----", raw, re.DOTALL)
    if not match:
        cleaned["private_key"] = raw
        return cleaned

    body = match.group(1)
    body = re.sub(r"\s+", "", body)

    if not body:
        cleaned["private_key"] = raw
        return cleaned

    normalized = "-----BEGIN PRIVATE KEY-----\n"
    normalized += "\n".join(textwrap.wrap(body, 64))
    normalized += "\n-----END PRIVATE KEY-----\n"
    cleaned["private_key"] = normalized
    return cleaned


@st.cache_resource(show_spinner=False)
def _get_google_credentials():
    credentials_info = st.secrets.get("gcp_service_account")
    if not credentials_info:
        raise RuntimeError("No se encontraron las credenciales de Google en st.secrets['gcp_service_account'].")
    normalized_info = _normalize_private_key(credentials_info)
    credentials = Credentials.from_service_account_info(normalized_info, scopes=SCOPES)
    return credentials


@st.cache_resource(show_spinner=False)
def _get_gspread_client():
    credentials = _get_google_credentials()
    return gspread.authorize(credentials)


def _get_spreadsheet(spreadsheet_id: str):
    if not spreadsheet_id:
        raise RuntimeError("No se encontró el ID de la hoja de cálculo de Google (SPREADSHEET_ID).")
    client = _get_gspread_client()
    return client.open_by_key(spreadsheet_id)


def _stringify_cell(value):
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and pd.isna(value):
        return ""
    return str(value)


def _write_dataframe_to_worksheet(ws, df: pd.DataFrame):
    df_to_write = df.copy()
    for col in df_to_write.columns:
        if df_to_write[col].dtype == "object":
            df_to_write[col] = df_to_write[col].fillna("")
        else:
            df_to_write[col] = df_to_write[col].where(~df_to_write[col].isna(), "")

    values = [df_to_write.columns.tolist()] + [
        [_stringify_cell(v) for v in row]
        for row in df_to_write.values.tolist()
    ]
    ws.clear()
    ws.update('A1', values if values else [df_to_write.columns.tolist()])


def _ensure_worksheet(sh, title: str, columns: List[str]):
    try:
        ws = sh.worksheet(title)
    except WorksheetNotFound:
        ws = sh.add_worksheet(title=title, rows=2, cols=max(20, len(columns)))
        ws.append_row(columns)
        return ws

    all_values = ws.get_all_values()
    if not all_values:
        ws.append_row(columns)
        return ws

    header = all_values[0]
    if header == columns:
        return ws

    existing_df = pd.DataFrame(all_values[1:], columns=header)
    for col in columns:
        if col not in existing_df.columns:
            existing_df[col] = ""
    existing_df = existing_df[columns]
    _write_dataframe_to_worksheet(ws, existing_df)
    return ws


def ensure_excel_with_sheets(spreadsheet_id: str):
    sh = _get_spreadsheet(spreadsheet_id)
    _ensure_worksheet(sh, "PARTICIPANTES", PARTICIPANTES_COLS)
    _ensure_worksheet(sh, "ACOMPANANTES", ACOMPANANTES_COLS)
    _ensure_worksheet(sh, "UNIFICADO", UNIFICADO_COLS)


def append_row(spreadsheet_id: str, sheet: str, row: list, expected_cols: list):
    sh = _get_spreadsheet(spreadsheet_id)
    ws = _ensure_worksheet(sh, sheet, expected_cols)
    prepared = [_stringify_cell(row[i]) if i < len(row) else "" for i in range(len(expected_cols))]
    ws.append_row(prepared, value_input_option="USER_ENTERED")


def _get_service_account_email() -> str:
    info = st.secrets.get("gcp_service_account")
    if isinstance(info, dict):
        email = info.get("client_email")
        if isinstance(email, str):
            return email
    return ""


def _record_drive_error(message: str) -> None:
    """Store the last Drive error so the UI can surface troubleshooting info."""
    if not message:
        st.session_state.pop("_drive_last_error", None)
        return
    st.session_state["_drive_last_error"] = message


def upload_file_to_drive(local_path: Path, folder_id: str = "") -> str:
    """Upload a file to Drive and return a shareable link.

    When a Shared Drive folder is provided the request must opt-in to
    ``supportsAllDrives`` or Drive rejects the upload. Streamlit users often
    store the destination folder inside a shared drive, so we set the flag
    both for the file upload and the permission share call.
    """
    if not isinstance(local_path, Path):
        local_path = Path(str(local_path))

    if not local_path.exists():
        _record_drive_error(f"El archivo {local_path} no existe para subirlo a Drive.")
        return ""

    try:
        credentials = _get_google_credentials()
    except RuntimeError as exc:
        _record_drive_error(str(exc))
        return ""

    session = AuthorizedSession(credentials)

    metadata = {"name": local_path.name}
    cleaned_folder = (folder_id or "").strip()
    if cleaned_folder:
        metadata["parents"] = [cleaned_folder]

    mime_type = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
    upload_url = "https://www.googleapis.com/upload/drive/v3/files"
    params = {
        "uploadType": "multipart",
        "supportsAllDrives": "true",
        "fields": "id,webViewLink,webContentLink",
    }

    try:
        with local_path.open("rb") as fh:
            files = {
                "metadata": (
                    "metadata",
                    json.dumps(metadata),
                    "application/json; charset=UTF-8",
                ),
                "file": (
                    local_path.name,
                    fh,
                    mime_type,
                ),
            }
            response = session.post(upload_url, params=params, files=files)
    except Exception as exc:
        _record_drive_error(f"Error al subir a Drive: {exc}")
        return ""

    if response.status_code not in (200, 201):
        error_text = response.text.strip()
        if response.status_code == 404 and cleaned_folder:
            service_email = _get_service_account_email()
            hint = (
                "No se encontró la carpeta de Drive indicada. "
                "Verifica que el ID sea correcto, que la carpeta exista y que el service account"
            )
            if service_email:
                hint += f" ({service_email})"
            hint += " tenga al menos permiso de Editor en esa carpeta o en la unidad compartida."
            _record_drive_error(hint)
        else:
            _record_drive_error(
                f"Error al subir a Drive (HTTP {response.status_code}): {error_text}"
            )
        return ""

    payload = response.json() if response.content else {}
    file_id = payload.get("id")
    web_view_link = payload.get("webViewLink")
    web_content_link = payload.get("webContentLink")

    if not file_id:
        _record_drive_error("La respuesta de Drive no incluyó un ID de archivo.")
        return ""

    permission_params = {
        "sendNotificationEmail": "false",
        "supportsAllDrives": "true",
        "fields": "id",
    }

    with suppress(Exception):
        session.post(
            f"https://www.googleapis.com/drive/v3/files/{file_id}/permissions",
            params=permission_params,
            json={"role": "reader", "type": "anyone"},
        )

    _record_drive_error("")

    for candidate in (web_view_link, web_content_link):
        if isinstance(candidate, str) and candidate.startswith("http"):
            return candidate

    return f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"


def get_sheet_as_dataframe(spreadsheet_id: str, sheet: str, expected_cols: list) -> pd.DataFrame:
    sh = _get_spreadsheet(spreadsheet_id)
    ws = _ensure_worksheet(sh, sheet, expected_cols)
    records = ws.get_all_records()
    df = pd.DataFrame(records)
    if df.empty:
        df = pd.DataFrame(columns=expected_cols)
    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
    df = df[expected_cols]
    return df

def _normalize_doc(s: str) -> str:
    return "".join(str(s or "").split())

def _docs_from_text(txt: str):
    if not isinstance(txt, str):
        return set()
    import re
    parts = re.split(r"[,;\n]+", txt)
    return set(p.strip().replace(" ","") for p in parts if p.strip())

def update_unificado(spreadsheet_id: str) -> int:
    sh = _get_spreadsheet(spreadsheet_id)
    p = get_sheet_as_dataframe(spreadsheet_id, "PARTICIPANTES", PARTICIPANTES_COLS)
    a = get_sheet_as_dataframe(spreadsheet_id, "ACOMPANANTES", ACOMPANANTES_COLS)

    # Mapa de acompañantes por documento
    acomp_map = {}
    for _, row in a.iterrows():
        docA = _normalize_doc(row.get("documento_acompanante",""))
        if not docA:
            continue
        acomp_map[docA] = {
            "nombre": row.get("nombre_acompanante",""),
            "archivo": row.get("archivo_lista_menores_url",""),
            "set_docs": _docs_from_text(row.get("lista_documentos_menores_texto","")),
        }

    out_rows = []
    for _, r in p.iterrows():
        docP = _normalize_doc(r.get("documento_participante",""))
        nombreP = r.get("nombre_completo","")
        esMayor = str(r.get("es_mayor_edad","")).lower() in ["true","si","sí"]
        docAcDecl = _normalize_doc(r.get("documento_contacto",""))
        matchAcud = "NO_APLICA"
        docAReal = ""
        nomAReal = ""
        tieneArchivo = "NO_APLICA"
        listaContiene = "NO_APLICA"
        obs = []

        if not esMayor:
            if not docAcDecl:
                matchAcud = "FALTA"
                obs.append("Menor sin documento de acudiente declarado.")
            else:
                acomp = acomp_map.get(docAcDecl)
                if acomp:
                    matchAcud = "OK"
                    docAReal = docAcDecl
                    nomAReal = acomp["nombre"]
                    if str(acomp["archivo"]).strip():
                        tieneArchivo = "TRUE"
                    else:
                        tieneArchivo = "FALSE"
                        obs.append("Acudiente sin archivo de consentimiento.")
                    if acomp["set_docs"]:
                        listaContiene = "TRUE" if docP in acomp["set_docs"] else "FALSE"
                        if listaContiene == "FALSE":
                            obs.append("El documento del menor no aparece en la lista del acudiente.")
                    else:
                        listaContiene = "NO_LISTA"
                        obs.append("Acudiente no diligenció la lista de documentos (campo de apoyo).")
                else:
                    matchAcud = "FALTA"
                    obs.append("No se encontró al acudiente en el Form de acompañantes.")

        out_rows.append([
            docP, nombreP, "TRUE" if esMayor else "FALSE", docAcDecl, matchAcud,
            docAReal, nomAReal, tieneArchivo, listaContiene, " | ".join(obs)
        ])

    out = pd.DataFrame(out_rows, columns=UNIFICADO_COLS)
    ws_unificado = _ensure_worksheet(sh, "UNIFICADO", UNIFICADO_COLS)
    _write_dataframe_to_worksheet(ws_unificado, out)
    return len(out_rows)


def subir_y_guardar_enlace(
    spreadsheet_id: str,
    sheet: str,
    columna_objetivo: str,
    clave_busqueda_col: str,
    clave_busqueda_val: str,
    local_path: str,
    folder_id: str = "",
) -> str:
    url = upload_file_to_drive(Path(local_path), folder_id=folder_id)
    if not url:
        raise RuntimeError(
            "No se pudo subir a Drive (revisa _drive_last_error en session_state)."
        )

    sh = _get_spreadsheet(spreadsheet_id)
    if sheet == "PARTICIPANTES":
        expected_cols = PARTICIPANTES_COLS
    elif sheet == "ACOMPANANTES":
        expected_cols = ACOMPANANTES_COLS
    else:
        expected_cols = UNIFICADO_COLS

    df = get_sheet_as_dataframe(spreadsheet_id, sheet, expected_cols)

    if columna_objetivo not in df.columns:
        df[columna_objetivo] = ""

    mask = df[clave_busqueda_col].astype(str).str.replace(r"\s+", "", regex=True).eq(
        str(clave_busqueda_val).replace(" ", "")
    )
    if not mask.any():
        raise RuntimeError(
            f"No se encontró la fila en {sheet} con {clave_busqueda_col}={clave_busqueda_val}"
        )

    df.loc[mask, columna_objetivo] = url

    ws = _ensure_worksheet(sh, sheet, list(df.columns))
    _write_dataframe_to_worksheet(ws, df)

    return url
