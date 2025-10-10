from pathlib import Path
import pandas as pd

PARTICIPANTES_COLS = [
    "timestamp","es_mayor_edad","tipo_documento_participante","documento_participante","nombre_completo",
    "como_te_gusta_que_te_digan","telefono_celular","correo","fecha_nacimiento","edad_aprox","eps",
    "restricciones_alimentarias","salud_mental","region","obra_institucion","proceso_juvenil",
    "intereses_personales","experiencia_significativa","dato_freak","pregunta_para_conectar",
    "exp_servicio_rank","exp_peregrinaje_rank","exp_cultura_arte_rank","exp_espiritualidad_rank","exp_vocacion_rank","exp_incidencia_politica_rank",
    "experiencia_top_calculada","perfil_cercania","motivo_experiencia_top","preguntas_frecuentes",
    "ha_vivido_acompanamiento","acompanamiento_parcerxs","acompanamiento_familia","acompanamiento_mentoria",
    "acompanamiento_espiritual","acompanamiento_emocional",
    "conoce_rji","tipo_documento_acudiente","documento_acudiente","nombre_acudiente","correo_acudiente","telefono_acudiente",
    "acepta_tratamiento_datos"
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

def ensure_excel_with_sheets(path: Path):
    path = Path(path)
    if not path.exists():
        with pd.ExcelWriter(path, engine="xlsxwriter") as writer:
            pd.DataFrame(columns=PARTICIPANTES_COLS).to_excel(writer, sheet_name="PARTICIPANTES", index=False)
            pd.DataFrame(columns=ACOMPANANTES_COLS).to_excel(writer, sheet_name="ACOMPANANTES", index=False)
            pd.DataFrame(columns=UNIFICADO_COLS).to_excel(writer, sheet_name="UNIFICADO", index=False)
    else:
        xl = pd.ExcelFile(path)
        with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="overlay") as writer:
            if "PARTICIPANTES" not in xl.sheet_names:
                pd.DataFrame(columns=PARTICIPANTES_COLS).to_excel(writer, sheet_name="PARTICIPANTES", index=False)
            if "ACOMPANANTES" not in xl.sheet_names:
                pd.DataFrame(columns=ACOMPANANTES_COLS).to_excel(writer, sheet_name="ACOMPANANTES", index=False)
            if "UNIFICADO" not in xl.sheet_names:
                pd.DataFrame(columns=UNIFICADO_COLS).to_excel(writer, sheet_name="UNIFICADO", index=False)

def append_row(path: Path, sheet: str, row: list, expected_cols: list):
    path = Path(path)
    df = pd.read_excel(path, sheet_name=sheet)
    if list(df.columns) != expected_cols:
        # añade columnas faltantes y reordena
        for c in expected_cols:
            if c not in df.columns:
                df[c] = ""
        df = df[expected_cols]
    new = pd.DataFrame([row], columns=expected_cols)
    df = pd.concat([df, new], ignore_index=True)
    with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        df.to_excel(writer, sheet_name=sheet, index=False)

def _normalize_doc(s: str) -> str:
    return "".join(str(s or "").split())

def _docs_from_text(txt: str):
    if not isinstance(txt, str):
        return set()
    import re
    parts = re.split(r"[,;\n]+", txt)
    return set(p.strip().replace(" ","") for p in parts if p.strip())

def update_unificado(path: Path) -> int:
    path = Path(path)
    p = pd.read_excel(path, sheet_name="PARTICIPANTES")
    a = pd.read_excel(path, sheet_name="ACOMPANANTES")

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
        docAcDecl = _normalize_doc(r.get("documento_acudiente",""))
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
    with pd.ExcelWriter(path, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
        out.to_excel(writer, sheet_name="UNIFICADO", index=False)
    return len(out_rows)
