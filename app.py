import streamlit as st
import pandas as pd
import io
import copy
from pathlib import Path
from datetime import datetime, date, time
from utils import (
    ensure_excel_with_sheets, append_row, update_unificado,
    PARTICIPANTES_COLS, ACOMPANANTES_COLS, UNIFICADO_COLS,
)

# Word para el documento de autorización en blanco
from docx import Document
from docx.shared import Pt, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# ===== CONFIG =====
EXCEL_PATH = Path("rji_datos.xlsx")       # cambia aquí si deseas otra ruta
BANNER_PATH = "assets/ClaveriadaBanner-1920x650.png"

st.set_page_config(
    page_title="Claveriado RJI · Inscripción",
    layout="centered",
    initial_sidebar_state="collapsed"     # oculta la barra lateral
)

# Asegura el Excel (no visible para usuarios)
ensure_excel_with_sheets(EXCEL_PATH)

# ===== Estilos (paleta Claveriada + ocultar sidebar) =====
st.markdown(
    """
    <style>
    /* Ocultar sidebar y el botón de despliegue */
    [data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none !important; }

    :root{
      --bg:#141d2c;           /* fondo principal */
      --card:#1b2a44;         /* tarjetas */
      --border:#243656;       /* bordes */
      --text:#e7eefc;         /* texto principal */
      --muted:#9fb1d0;        /* texto secundario */
      --accent:#ff9c2a;       /* naranja */
      --accent2:#8bd143;      /* verde */
      --accent3:#9cc5ff;      /* azul claro */
      --radius:18px;
    }
    .main{ background:var(--bg); }
    .block-container{ padding-top:1rem; padding-bottom:3rem; max-width:980px; }
    .rji-card{
      background:var(--card); border:1px solid var(--border);
      border-radius:var(--radius); padding:1.25rem 1.5rem;
      box-shadow:0 16px 40px rgba(0,0,0,.35);
    }
    .rji-title{ color:var(--text); font-size:2rem; font-weight:800; margin:.2rem 0 .2rem; }
    .rji-sub{ color:var(--muted); margin-bottom:1.2rem; font-size:.98rem; }
    .stTabs [data-baseweb="tab-list"]{ gap:6px; }
    .stTabs [data-baseweb="tab"]{
      background:var(--card); border-radius:999px; padding:.45rem .95rem;
      border:1px solid var(--border); color:var(--text);
    }
    .stTabs [aria-selected="true"]{
      border:1px solid var(--accent); background:#233658; color:var(--accent);
    }
    .stage-progress{ margin:1.25rem 0 .5rem; }
    .stage-progress-label{ display:flex; justify-content:space-between; font-weight:600; color:var(--text); margin-bottom:.35rem; }
    .stage-progress-bar{ background:rgba(255,255,255,.12); border-radius:999px; height:16px; overflow:hidden; border:1px solid var(--border); }
    .stage-progress-bar span{ display:block; height:100%; background:linear-gradient(90deg,var(--accent),var(--accent3)); border-radius:inherit; transition:width .35s ease; }
    .stage-progress-sub{ color:var(--muted); font-size:.92rem; margin-top:.25rem; }
    .motivacion-box{ background:rgba(255,156,42,.12); border:1px solid rgba(255,156,42,.35); color:var(--accent); padding:.75rem 1rem; border-radius:12px; font-weight:600; }
    .ranking-guide{ display:flex; justify-content:space-between; gap:.5rem; margin:0 0 1rem; }
    .ranking-guide span{ flex:1; text-align:center; background:rgba(156,197,255,.14); border:1px solid rgba(156,197,255,.35); padding:.45rem 0; border-radius:10px; font-weight:600; color:var(--text); }
    .perfil-slider-labels{ display:flex; justify-content:space-between; color:var(--muted); font-weight:600; margin-top:.35rem; }
    /* Inputs */
    label, .stMarkdown, .stCaption, .stRadio, .stText, .stSelectbox, .stDateInput, .stTimeInput{
      color:var(--text) !important;
    }
    .stTextInput>div>div>input, .stTextArea textarea{
      background:var(--bg) !important; color:var(--text) !important; border-radius:10px;
      border:1px solid var(--border) !important;
    }
    .stSelectbox>div>div{ background:var(--bg) !important; border-radius:10px; border:1px solid var(--border); }
    .stDateInput>div>div, .stTimeInput>div>div{
      background:var(--bg) !important; border:1px solid var(--border) !important; border-radius:10px;
    }
    /* Botones */
    .stButton>button, .stDownloadButton>button{
      background:var(--accent); color:#1a1625; border:1px solid var(--accent);
      border-radius:10px; padding:.5rem 1rem; font-weight:700;
    }
    .stButton>button:hover, .stDownloadButton>button:hover{ filter:brightness(1.05); }

    /* Banner con bordes redondeados */
    .banner-wrap img{ border-radius:16px; border:1px solid var(--border); }
    </style>
    """,
    unsafe_allow_html=True
)

# ===== Banner =====
try:
    st.markdown('<div class="banner-wrap">', unsafe_allow_html=True)
    st.image(BANNER_PATH, use_column_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
except Exception:
    pass
st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

# ===== Header =====
st.markdown('<div class="rji-card">', unsafe_allow_html=True)
st.markdown('<div class="rji-title">Inscripciones · RJI</div>', unsafe_allow_html=True)
st.markdown('<div class="rji-sub">Participantes y Acompañantes — Medellín, Colombia</div>', unsafe_allow_html=True)

# ===== Pestañas =====
tab1, tab2 = st.tabs(["Participante", "Acompañante/Acudiente"])

# ===== Utilidades =====
def crear_doc_autorizacion_en_blanco(logo_path="assets/logo.png"):
    """Documento Word en blanco (no depende de datos)."""
    doc = Document()
    section = doc.sections[0]
    section.top_margin = Cm(2); section.bottom_margin = Cm(2); section.left_margin = Cm(2); section.right_margin = Cm(2)
    try:
        if Path(logo_path).exists():
            header = doc.sections[0].header
            hdr_p = header.paragraphs[0]
            run = hdr_p.add_run()
            run.add_picture(logo_path, width=Inches(3.0))
    except Exception:
        pass
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("FORMATO DE AUTORIZACIÓN Y ACOMPAÑAMIENTO"); r.bold = True; r.font.size = Pt(16)
    s = doc.add_paragraph(); s.alignment = WD_ALIGN_PARAGRAPH.CENTER
    s.add_run("Claveriada RJI – Medellín, Colombia").font.size = Pt(12)
    info = doc.add_paragraph()
    info.add_run("La información consignada es sensible y será utilizada únicamente para construir el perfil de cada participante "
                 "en la Claveriada RJI y para la logística del encuentro. No será compartida con terceros.\n").font.size = Pt(10)
    a = doc.add_paragraph()
    a.add_run("Yo, ________________________________, identificado(a) con documento No. ________________________, "
              "en calidad de acudiente/acompañante, autorizo la participación de las/los siguientes jóvenes en el evento.").font.size = Pt(11)
    t = doc.add_table(rows=2, cols=2); t.style = "Table Grid"
    t.cell(0,0).text = "Correo del acompañante"; t.cell(0,1).text = "_______________________________"
    t.cell(1,0).text = "Teléfono del acompañante"; t.cell(1,1).text = "_______________________________"
    doc.add_paragraph().add_run("Relación de jóvenes a cargo").bold = True
    tbl = doc.add_table(rows=1, cols=5); tbl.style = "Table Grid"
    hdr = tbl.rows[0].cells
    hdr[0].text = "Nombre completo"; hdr[1].text = "Documento"; hdr[2].text = "Edad"; hdr[3].text = "EPS"; hdr[4].text = "Complicaciones de salud"
    for _ in range(6):
        row = tbl.add_row().cells
        for i in range(5): row[i].text = ""
    doc.add_paragraph("Declaro que la información es veraz y me comprometo a acompañar y velar por el bienestar de las/los jóvenes, "
                      "cumplir las indicaciones del equipo organizador y notificar cualquier situación de salud o emergencia.")
    f = doc.add_table(rows=2, cols=2); f.autofit = True
    f.cell(0,0).text = "\n\n_______________________________"
    f.cell(0,1).text = "\n\n_______________________________"
    f.cell(1,0).text = "Firma del acompañante"
    f.cell(1,1).text = "Firma de la institución"
    return doc

def calcular_edad(fecha_str):
    if not fecha_str:
        return ""
    try:
        d = pd.to_datetime(str(fecha_str), errors="coerce")
        if pd.isna(d): return ""
        today = pd.Timestamp.today().date()
        d = d.date()
        return today.year - d.year - ((today.month, today.day) < (d.month, d.day))
    except Exception:
        return ""

PARTICIPANT_DEFAULTS = {
    "part_step": 1,
    "part_es_mayor_option": "",
    "part_tipo_doc_p": "",
    "part_doc_p": "",
    "part_nombre": "",
    "part_apodo": "",
    "part_tel": "",
    "part_correo": "",
    "part_fecha_nac": date(2006, 1, 1),
    "part_eps": "",
    "part_rest_alim": "",
    "part_salud_mental": "",
    "part_region": "",
    "part_obra": "",
    "part_proceso": "",
    "part_tipo_doc_a": "",
    "part_doc_a": "",
    "part_nom_a": "",
    "part_correo_a": "",
    "part_tel_a": "",
    "part_exp_sig": "",
    "part_intereses": [],
    "part_dato_freak": "",
    "part_pregunta": "",
    "part_motivo": "",
    "part_preguntas_frec": "",
    "part_acomp_viv": "",
    "part_acomp_parcerxs": False,
    "part_acomp_familia": False,
    "part_acomp_mentoria": False,
    "part_acomp_espiritual": False,
    "part_acomp_emocional": False,
    "part_acomp_red_comunidad": False,
    "part_conoce_rji": "",
    "part_acepta_datos": False,
    "part_perfil_slider": 1,
}


def _init_participant_state():
    for key, value in PARTICIPANT_DEFAULTS.items():
        if key not in st.session_state:
            st.session_state[key] = copy.deepcopy(value)


def _participant_stage_fields(stage: int):
    base = {
        1: [
            "part_es_mayor_option", "part_tipo_doc_p", "part_doc_p", "part_nombre",
            "part_apodo", "part_tel", "part_correo", "part_fecha_nac", "part_eps",
            "part_rest_alim", "part_salud_mental", "part_region", "part_obra", "part_proceso",
        ],
        2: [
            "part_exp_sig", "part_intereses", "part_dato_freak", "part_pregunta",
        ],
        3: [
            "part_motivo", "part_preguntas_frec", "part_acomp_viv",
            "part_acomp_parcerxs", "part_acomp_familia", "part_acomp_mentoria",
            "part_acomp_espiritual", "part_acomp_emocional", "part_acomp_red_comunidad", "part_conoce_rji",
            "part_acepta_datos",
        ],
    }
    if stage == 1 and st.session_state.get("part_es_mayor_option") == "No":
        base[1].extend([
            "part_tipo_doc_a", "part_doc_a", "part_nom_a", "part_correo_a", "part_tel_a",
        ])
    return base.get(stage, [])


def _value_is_filled(val, key: str) -> bool:
    optional_blanks = {"part_apodo", "part_salud_mental", "part_preguntas_frec", "part_acomp_viv"}
    if key in optional_blanks:
        return True
    if key == "part_acepta_datos":
        return bool(val)
    if isinstance(val, str):
        return bool(val.strip())
    if isinstance(val, list):
        return len(val) > 0
    if isinstance(val, bool):
        if key.startswith("part_acomp_"):
            return True
        return bool(val)
    if isinstance(val, (date, datetime)):
        if key == "part_fecha_nac" and isinstance(val, date) and val == PARTICIPANT_DEFAULTS["part_fecha_nac"]:
            return False
        return True
    if val is None:
        return False
    return True


def _stage_progress(stage: int):
    fields = _participant_stage_fields(stage)
    if not fields:
        return 0.0, 0, 0, 0
    answered = sum(1 for key in fields if _value_is_filled(st.session_state.get(key), key))
    total = len(fields)
    return answered / total, int(round((answered / total) * 100)), answered, total


def _goto_participant_stage(stage: int):
    st.session_state.part_step = stage


_init_participant_state()

# ================= PARTICIPANTE =================
with tab1:
    stage = st.session_state.part_step
    stage_titles = {
        1: "Etapa 1 · Datos personales",
        2: "Etapa 2 · Historial e intereses",
        3: "Etapa 3 · Experiencias y acompañamiento",
    }
    motivaciones = {
        1: "Vamos paso a paso, comparte quién eres para arrancar con buen pie 💪",
        2: "¡Bien! Ya casi llegamos a las experiencias, cuéntanos lo que te mueve ✨",
        3: "Último tramo, vamos con toda para elegir experiencias y acompañamientos 🚀",
    }

    st.markdown(f"### {stage_titles.get(stage, '')}")
    progreso, porcentaje, respondidas, total = _stage_progress(stage)
    barra = max(porcentaje, 4) if porcentaje > 0 else 4
    st.markdown(
        f"""
        <div class=\"stage-progress\">
            <div class=\"stage-progress-label\">
                <span>Avance de la etapa</span>
                <span>{porcentaje}%</span>
            </div>
            <div class=\"stage-progress-bar\">
                <span style=\"width:{barra}%\"></span>
            </div>
        </div>
        <div class=\"stage-progress-sub\">Has respondido {respondidas} de {total} preguntas clave en esta sección.</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"<div class='motivacion-box'>{motivaciones.get(stage, '')}</div>", unsafe_allow_html=True)

    if stage > 1:
        st.button("⬅️ Volver a la etapa anterior", on_click=lambda: _goto_participant_stage(stage - 1))

    experiencias = ["Servicio", "Peregrinaje", "Cultura y arte", "Espiritualidad", "Vocación", "Incidencia política"]

    if stage == 1:
        with st.form("form_participante_stage1", clear_on_submit=False):
            st.subheader("Información básica")
            mayor_opciones = ["", "Sí", "No"]
            es_mayor = st.radio(
                "¿Eres mayor de edad?",
                mayor_opciones,
                horizontal=True,
                index=mayor_opciones.index(st.session_state.get("part_es_mayor_option", "")),
                format_func=lambda opt: "Selecciona una opción" if opt == "" else opt,
            )
            st.session_state.part_es_mayor_option = es_mayor

            doc_options = ["Selecciona tu documento", "CC", "TI", "CE", "Pasaporte", "Otro"]
            current_doc = st.session_state.get("part_tipo_doc_p") or doc_options[0]
            tipo_doc = st.selectbox(
                "Tipo de documento",
                doc_options,
                index=doc_options.index(current_doc) if current_doc in doc_options else 0,
            )
            st.session_state.part_tipo_doc_p = "" if tipo_doc == doc_options[0] else tipo_doc
            st.text_input("Número de documento (solo dígitos)", max_chars=20, placeholder="Ej: 1234567890", key="part_doc_p")
            st.text_input("Nombre completo", placeholder="Nombres y apellidos", key="part_nombre")
            st.text_input("¿Cómo te gusta que te digan?", placeholder="Opcional", key="part_apodo")
            st.text_input("Teléfono celular", placeholder="+57 ...", key="part_tel")
            st.text_input("Correo", placeholder="tu@correo.com", key="part_correo")
            st.date_input(
                "Fecha de nacimiento",
                min_value=date(1900, 1, 1),
                max_value=date.today(),
                key="part_fecha_nac"
            )
            st.text_input("EPS", placeholder="Escribe tu EPS", key="part_eps")
            st.text_input(
                "Restricciones alimentarias (o 'ninguna')",
                placeholder="Vegetariano, alergias, etc.",
                key="part_rest_alim"
            )
            st.text_area(
                "Complicaciones/alertas de salud (solo lo necesario para cuidarte mejor)",
                key="part_salud_mental"
            )
            st.text_input("Región", placeholder="Ciudad / Departamento", key="part_region")
            st.text_input(
                "¿De qué obra / institución vienes?",
                placeholder="Colegio, parroquia, movimiento...",
                key="part_obra"
            )
            st.text_input(
                "¿Perteneces a algún proceso juvenil? ¿Cuál?",
                placeholder="Nombre del proceso",
                key="part_proceso"
            )

            if st.session_state.get("part_es_mayor_option") == "No":
                st.subheader("Datos del acudiente")
                doc_ac_options = ["Selecciona el documento", "CC", "CE", "Pasaporte", "Otro"]
                current_doc_a = st.session_state.get("part_tipo_doc_a") or doc_ac_options[0]
                tipo_doc_a = st.selectbox(
                    "Tipo de documento (acudiente)",
                    doc_ac_options,
                    index=doc_ac_options.index(current_doc_a) if current_doc_a in doc_ac_options else 0,
                )
                st.session_state.part_tipo_doc_a = "" if tipo_doc_a == doc_ac_options[0] else tipo_doc_a
                st.text_input(
                    "Documento del acudiente (solo dígitos)",
                    max_chars=20,
                    placeholder="Ej: 1012345678",
                    key="part_doc_a"
                )
                st.text_input("Nombre del acudiente", key="part_nom_a")
                st.text_input("Correo del acudiente", key="part_correo_a")
                st.text_input("Teléfono del acudiente", key="part_tel_a")

            if st.form_submit_button("Continuar a intereses", use_container_width=True):
                if st.session_state.get("part_es_mayor_option") == "":
                    st.warning("Porfa, cuéntanos si eres mayor de edad para continuar.")
                else:
                    _goto_participant_stage(2)

    elif stage == 2:
        intereses_full = [
            "Aventura", "Deporte", "Contemplación", "Arte", "Música", "Danza", "Teatro", "Fotografía",
            "Ciencia", "Tecnología", "Videojuegos", "Cocina", "Emprendimiento", "Lectura", "Naturaleza",
            "Montaña", "Ciclismo", "Senderismo", "Viajes", "Idiomas", "Servicio comunitario", "Liderazgo", "Mascotas"
        ]
        with st.form("form_participante_stage2", clear_on_submit=False):
            st.subheader("Momentos que te han marcado")
            st.text_area(
                "Experiencia juvenil significativa (torneo, voluntariado, congreso, etc.)",
                key="part_exp_sig"
            )
            st.multiselect(
                "Intereses personales",
                intereses_full,
                key="part_intereses"
            )
            st.text_input("Dato freak de ti", placeholder="Algo curioso sobre ti", key="part_dato_freak")
            st.text_input("Propón una pregunta para conectar con otros", key="part_pregunta")

            col1, col2 = st.columns([1, 1])
            avanzar = col1.form_submit_button("Ir a experiencias", use_container_width=True)
            volver = col2.form_submit_button("Volver a datos", use_container_width=True)
            if volver:
                _goto_participant_stage(1)
            elif avanzar:
                _goto_participant_stage(3)

    else:  # stage 3
        with st.form("form_participante_stage3", clear_on_submit=False):
            st.subheader("Así ordenas tus experiencias")
            st.markdown(
                """
                <div class=\"ranking-guide\">
                    <span>1</span>
                    <span>2</span>
                    <span>3</span>
                    <span>4</span>
                    <span>5</span>
                    <span>6</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            try:
                from streamlit_sortables import sort_items  # type: ignore
                st.caption("Arrastra para ordenar según tu interés (arriba = más interés)")
                order = sort_items(experiencias, direction="vertical", key="exp_sort")
            except Exception:
                st.caption("Selecciona en orden de interés (sin repetir).")

                def ranker(options):
                    remaining = options.copy()
                    selected = []
                    for i in range(len(options)):
                        choice = st.selectbox(f"Puesto {i+1}", remaining, key=f"rank_{i}")
                        selected.append(choice)
                        remaining = [o for o in remaining if o != choice]
                    return selected

                order = ranker(experiencias)

            ranks = {exp: (order.index(exp) + 1) for exp in experiencias}

            st.markdown("#### Perfil de cercanía con la priorizada")
            st.slider(
                "Mueve la barra para ubicarte",
                min_value=1,
                max_value=3,
                step=1,
                key="part_perfil_slider"
            )
            perfil_map = {1: "Curioso", 2: "Explorador", 3: "Protagonista"}
            seleccionado = st.session_state.get("part_perfil_slider", 1)
            st.markdown(
                """
                <div class=\"perfil-slider-labels\">
                    <span>⭐ Curioso</span>
                    <span>⭐⭐ Explorador</span>
                    <span>⭐⭐⭐ Protagonista</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            perfil_cerc = perfil_map[seleccionado]

            st.text_area(
                "¿Por qué te interesa la experiencia que pusiste de primera?",
                max_chars=500,
                help="Puedes usar hasta 500 caracteres para contarnos tu motivación.",
                key="part_motivo"
            )
            st.text_area(
                "¿Tienes alguna pregunta sobre esa experiencia?",
                key="part_preguntas_frec"
            )

            st.markdown("#### Acompañamiento")
            st.text_area(
                "Cuéntanos más de tu experiencia de acompañamiento",
                key="part_acomp_viv"
            )
            st.caption("Marca los acompañamientos con los que cuentas o quisieras fortalecer.")
            col_a, col_b, col_c = st.columns(3)
            col_d, col_e, col_f = st.columns(3)
            col_a.checkbox("Amistades", key="part_acomp_parcerxs")
            col_b.checkbox("Familia", key="part_acomp_familia")
            col_c.checkbox("Mentoría o tutoría", key="part_acomp_mentoria")
            col_d.checkbox("Acompañamiento espiritual", key="part_acomp_espiritual")
            col_e.checkbox("Escucha activa / apoyo emocional", key="part_acomp_emocional")
            col_f.checkbox("Red comunitaria o institucional", key="part_acomp_red_comunidad")

            conoce_opciones = ["Sí", "No", "Más o menos"]
            conoce_val = st.session_state.get("part_conoce_rji", "")
            conoce_idx = conoce_opciones.index(conoce_val) if conoce_val in conoce_opciones else None
            conoce_rji = st.radio(
                "¿Conoces qué es la RJI?",
                conoce_opciones,
                horizontal=True,
                index=conoce_idx,
            )
            st.session_state.part_conoce_rji = conoce_rji or ""

            st.markdown("---")
            st.caption("Aviso de privacidad: la información recolectada es sensible y se utilizará únicamente para construir tu perfil en la Claveriada RJI y para la logística del encuentro. No será compartida con terceros.")
            st.checkbox(
                "Acepto el tratamiento de datos con el propósito descrito",
                key="part_acepta_datos"
            )

            enviado = st.form_submit_button("Guardar participante", use_container_width=True)
            if enviado:
                es_mayor = st.session_state.get("part_es_mayor_option") == "Sí"
                doc_p = st.session_state.get("part_doc_p", "")
                doc_a = st.session_state.get("part_doc_a", "")
                nom_a = st.session_state.get("part_nom_a", "")
                if st.session_state.get("part_conoce_rji") == "":
                    st.error("Cuéntanos si conoces la RJI antes de guardar.")
                elif not st.session_state.get("part_acepta_datos"):
                    st.error("Debes aceptar el aviso de privacidad.")
                elif not doc_p.strip().isdigit():
                    st.error("El documento del participante debe contener solo dígitos.")
                elif not st.session_state.get("part_tipo_doc_p"):
                    st.error("Selecciona el tipo de documento del participante.")
                elif not st.session_state.get("part_es_mayor_option"):
                    st.error("Confírmanos si eres mayor de edad para continuar.")
                elif (not es_mayor) and (not doc_a.strip().isdigit() or not nom_a.strip() or not st.session_state.get("part_tipo_doc_a")):
                    st.error("Para menores, el documento y nombre del acudiente son obligatorios (solo dígitos en el documento).")
                else:
                    ts = datetime.now().isoformat(timespec="seconds")
                    intereses = st.session_state.get("part_intereses", [])
                    conoce_map = {"Sí": "Si", "No": "No", "Más o menos": "Mas o menos", "": ""}
                    row = [
                        ts,
                        "TRUE" if es_mayor else "FALSE",
                        st.session_state.get("part_tipo_doc_p", ""),
                        doc_p.strip(),
                        st.session_state.get("part_nombre", "").strip(),
                        st.session_state.get("part_apodo", "").strip(),
                        st.session_state.get("part_tel", "").strip(),
                        st.session_state.get("part_correo", "").strip(),
                        str(st.session_state.get("part_fecha_nac")),
                        "",
                        st.session_state.get("part_eps", "").strip(),
                        st.session_state.get("part_rest_alim", "").strip(),
                        st.session_state.get("part_salud_mental", "").strip(),
                        st.session_state.get("part_region", "").strip(),
                        st.session_state.get("part_obra", "").strip(),
                        st.session_state.get("part_proceso", "").strip(),
                        ", ".join(intereses),
                        st.session_state.get("part_exp_sig", "").strip(),
                        st.session_state.get("part_dato_freak", "").strip(),
                        st.session_state.get("part_pregunta", "").strip(),
                        int(ranks["Servicio"]),
                        int(ranks["Peregrinaje"]),
                        int(ranks["Cultura y arte"]),
                        int(ranks["Espiritualidad"]),
                        int(ranks["Vocación"]),
                        int(ranks["Incidencia política"]),
                        "",
                        perfil_cerc,
                        st.session_state.get("part_motivo", "").strip(),
                        st.session_state.get("part_preguntas_frec", "").strip(),
                        st.session_state.get("part_acomp_viv", "").strip(),
                        "TRUE" if st.session_state.get("part_acomp_parcerxs") else "FALSE",
                        "TRUE" if st.session_state.get("part_acomp_familia") else "FALSE",
                        "TRUE" if st.session_state.get("part_acomp_mentoria") else "FALSE",
                        "TRUE" if st.session_state.get("part_acomp_espiritual") else "FALSE",
                        "TRUE" if st.session_state.get("part_acomp_emocional") else "FALSE",
                        "TRUE" if st.session_state.get("part_acomp_red_comunidad") else "FALSE",
                        conoce_map.get(st.session_state.get("part_conoce_rji"), ""),
                        st.session_state.get("part_tipo_doc_a", ""),
                        doc_a.strip(),
                        nom_a.strip(),
                        st.session_state.get("part_correo_a", "").strip(),
                        st.session_state.get("part_tel_a", "").strip(),
                        "TRUE" if st.session_state.get("part_acepta_datos") else "FALSE",
                    ]
                    try:
                        append_row(EXCEL_PATH, "PARTICIPANTES", row, PARTICIPANTES_COLS)
                        try:
                            update_unificado(EXCEL_PATH)
                        except Exception:
                            pass
                        st.success("¡Tu registro quedó guardado! Gracias por llegar al final ✨")
                        for key, value in PARTICIPANT_DEFAULTS.items():
                            st.session_state[key] = copy.deepcopy(value)
                        st.session_state.pop("exp_sort", None)
                    except Exception as e:
                        st.error(f"No se pudo guardar: {e}")

# ================= ACOMPAÑANTE =================
with tab2:
    st.info("Para llenar este formulario debes tener organizados y a la mano los documentos de las y los participantes menores de edad de tu delegación.")
    with st.form("form_acompanante", clear_on_submit=False):
        st.markdown("#### Datos personales del acompañante / acudiente")
        tipo_doc_ac = st.selectbox("Tipo de documento", ["CC", "CE", "Pasaporte", "Otro"])
        doc_ac = st.text_input("Documento (solo dígitos)", max_chars=20, placeholder="Ej: 1012345678")
        nom_ac = st.text_input("Nombre completo")
        correo_ac = st.text_input("Correo")
        tel_ac = st.text_input("Teléfono")
        organiz = st.text_input("Organización (si aplica)")
        region_ac = st.text_input("Región")
        rol = st.text_input("Rol en la organización (si aplica)")

        st.markdown("#### Información de tu delegación")
        delegacion = st.text_input("¿A qué delegación acompañas?")
        total_personas = st.number_input(
            "¿Cuántas personas componen tu delegación (incluyéndote)?",
            min_value=1,
            step=1,
            value=1,
        )
        medio_viaje = st.radio("¿Por qué medio viajan?", ["Por tierra", "Por aire"], horizontal=True)
        trae_varios = st.radio("¿Traes varios jóvenes además de ti?", ["Sí", "No"], horizontal=True) == "Sí"

        st.markdown("#### Según tus experiencias, cuéntanos tu nivel en cada tipología")
        st.caption("Mueve las barras del 1 al 100 para ubicarnos en tu nivel de experticia acompañando cada experiencia.")
        exp_tipos = ["Servicio", "Peregrinaje", "Cultura y arte", "Espiritualidad", "Vocación", "Incidencia política"]
        niveles_experiencias = {}
        for exp in exp_tipos:
            niveles_experiencias[exp] = st.slider(exp, min_value=1, max_value=100, value=50)

        st.markdown("#### Logística Medellín")
        ciudad_origen = st.text_input("Ciudad de origen del grupo")
        hora_llegada = st.time_input("¿A qué hora llegará el grupo a Medellín?", value=time(14, 0))

        st.markdown("#### Consentimiento y relación de menores")
        st.warning("Este documento solo debe diligenciarse para participantes menores de edad.")
        archivo = st.file_uploader("Sube el archivo (PDF/Excel/Imagen) con la lista firmada de menores", type=["pdf", "xlsx", "xls", "csv", "png", "jpg", "jpeg"])
        st.caption("Además del archivo, puedes escribir abajo los documentos para validar automáticamente (opcional).")
        lista_texto = st.text_area("Escribe los documentos de los menores separados por coma (opcional)")

        enviado2 = st.form_submit_button("Guardar acompañante", use_container_width=True)
        if enviado2:
            if not doc_ac.strip().isdigit():
                st.error("El documento del acompañante debe contener solo dígitos.")
            elif not nom_ac.strip():
                st.error("El nombre del acompañante es obligatorio.")
            else:
                ts = datetime.now().isoformat(timespec="seconds")
                save_url = ""
                if archivo is not None:
                    up = Path("uploads"); up.mkdir(exist_ok=True)
                    file_path = up / f"{doc_ac.strip()}_{archivo.name}"
                    with open(file_path, "wb") as f:
                        f.write(archivo.getbuffer())
                    save_url = str(file_path)

                niveles_serializados = "; ".join(f"{exp}: {nivel}" for exp, nivel in niveles_experiencias.items())

                row = [
                    ts,
                    tipo_doc_ac,
                    doc_ac.strip(),
                    nom_ac.strip(),
                    correo_ac.strip(),
                    tel_ac.strip(),
                    organiz.strip(),
                    region_ac.strip(),
                    rol.strip(),
                    delegacion.strip(),
                    int(total_personas),
                    medio_viaje,
                    "TRUE" if trae_varios else "FALSE",
                    niveles_serializados,
                    ciudad_origen.strip(),
                    hora_llegada.strftime("%H:%M"),
                    save_url,
                    lista_texto.strip(),
                ]
                try:
                    append_row(EXCEL_PATH, "ACOMPANANTES", row, ACOMPANANTES_COLS)
                    try:
                        update_unificado(EXCEL_PATH)
                    except Exception:
                        pass
                    st.success("Acompañante guardado.")
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

    st.markdown("### Documento para firmar")
    st.caption("Descarga un formato de autorización en blanco para diligenciar y firmar.")
    if st.button("Descargar formato de autorización (en blanco)", use_container_width=True):
        docx = crear_doc_autorizacion_en_blanco("assets/logo.png")
        bio = io.BytesIO(); docx.save(bio); bio.seek(0)
        st.download_button(
            "Descargar ahora",
            data=bio,
            file_name="formato_autorizacion_rji.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            use_container_width=True
        )

st.markdown("</div>", unsafe_allow_html=True)
