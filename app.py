import streamlit as st
import pandas as pd
import io
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

# ================= PARTICIPANTE =================
with tab1:
    with st.form("form_participante", clear_on_submit=False):
        st.markdown("#### Datos personales")
        es_mayor = st.radio("¿Eres mayor de edad?", ["Sí","No"], horizontal=True) == "Sí"
        tipo_doc_p = st.selectbox("Tipo de documento", ["CC","TI","CE","Pasaporte","Otro"])
        doc_p = st.text_input("Número de documento (solo dígitos)", max_chars=20, placeholder="Ej: 1234567890")
        nombre = st.text_input("Nombre completo", placeholder="Nombres y apellidos")
        apodo = st.text_input("¿Cómo te gusta que te digan?", placeholder="Opcional")
        tel = st.text_input("Teléfono celular", placeholder="+57 ...")
        correo = st.text_input("Correo", placeholder="tu@correo.com")
        fecha_nac = st.date_input("Fecha de nacimiento", min_value=date(1900,1,1), max_value=date.today())
        eps = st.text_input("EPS", placeholder="Escribe tu EPS")
        rest_alim = st.text_input("Restricciones alimentarias (o 'ninguna')", placeholder="Vegetariano, alergias, etc.")
        salud_mental = st.text_area("Complicaciones/alertas de salud (solo lo necesario para cuidarte mejor)")
        region = st.text_input("Región", placeholder="Ciudad / Departamento")
        obra = st.text_input("¿De qué obra / institución vienes?", placeholder="Colegio, parroquia, movimiento...")
        proceso = st.text_input("¿Perteneces a algún proceso juvenil? ¿Cuál?", placeholder="Nombre del proceso")

        if not es_mayor:
            st.markdown("#### Datos del acudiente")
            tipo_doc_a = st.selectbox("Tipo de documento (acudiente)", ["CC","CE","Pasaporte","Otro"])
            doc_a = st.text_input("Documento del acudiente (solo dígitos)", max_chars=20, placeholder="Ej: 1012345678")
            nom_a = st.text_input("Nombre del acudiente")
            correo_a = st.text_input("Correo del acudiente")
            tel_a = st.text_input("Teléfono del acudiente")
        else:
            tipo_doc_a = ""; doc_a = ""; nom_a = ""; correo_a = ""; tel_a = ""

        st.markdown("#### Historial e intereses")
        exp_sig = st.text_area("Experiencia juvenil significativa (torneo, voluntariado, congreso, etc.)")
        intereses_full = [
            "Aventura","Deporte","Contemplación","Arte","Música","Danza","Teatro","Fotografía",
            "Ciencia","Tecnología","Videojuegos","Cocina","Emprendimiento","Lectura","Naturaleza",
            "Montaña","Ciclismo","Senderismo","Viajes","Idiomas","Servicio comunitario","Liderazgo","Mascotas"
        ]
        intereses = st.multiselect("Intereses personales", intereses_full, default=[])
        dato_freak = st.text_input("Dato freak de ti", placeholder="Algo curioso sobre ti")
        pregunta = st.text_input("Propón una pregunta para conectar con otros")

        st.markdown("#### Experiencias")
        experiencias = ["Servicio","Peregrinaje","Cultura y arte","Espiritualidad","Vocación","Incidencia política"]
        # Drag & drop si está disponible; si no, selector sin repetidos
        try:
            from streamlit_sortables import sort_items  # pip install streamlit-sortables
            st.caption("Arrastra para ordenar según tu interés (arriba = más interés)")
            order = sort_items(experiencias, direction="vertical", key="exp_sort")
        except Exception:
            st.caption("Selecciona en orden de interés (sin repetir).")
            def ranker(options):
                remaining = options.copy()
                selected=[]
                for i in range(len(options)):
                    choice = st.selectbox(f"Puesto {i+1}", remaining, key=f"rank_{i}")
                    selected.append(choice)
                    remaining = [o for o in remaining if o != choice]
                return selected
            order = ranker(experiencias)
        ranks = {exp: (order.index(exp)+1) for exp in experiencias}

        perfil_cerc = st.radio("Perfil de cercanía con la priorizada", ["Curioso","Explorador","Protagonista"], horizontal=True)
        motivo = st.text_area("¿Por qué te interesa la experiencia que pusiste de primera?")
        preguntas_frec = st.text_area("¿Tienes alguna pregunta sobre esa experiencia?")

        st.markdown("#### Acompañamiento")
        acomp_viv = st.text_input("¿Has vivido algún espacio de acompañamiento? ¿Cuál?")
        colA, colB, colC = st.columns(3)
        acomp_esp = colA.checkbox("Espiritual")
        acomp_psico = colB.checkbox("Psicológico")
        acomp_esc = colC.checkbox("Escucha activa")

        conoce_rji = st.radio("¿Conoces qué es la RJI?", ["Sí","No","Más o menos"], horizontal=True)

        st.markdown("---")
        st.caption("Aviso de privacidad: la información recolectada es sensible y se utilizará únicamente para construir tu perfil en la Claveriada RJI y para la logística del encuentro. No será compartida con terceros.")
        acepta_datos = st.checkbox("Acepto el tratamiento de datos con el propósito descrito", value=False)

        enviado = st.form_submit_button("Guardar participante", use_container_width=True)
        if enviado:
            if not acepta_datos:
                st.error("Debes aceptar el aviso de privacidad.")
            elif not doc_p.strip().isdigit():
                st.error("El documento del participante debe contener solo dígitos.")
            elif (not es_mayor) and (not doc_a.strip().isdigit() or not nom_a.strip()):
                st.error("Para menores, el documento y nombre del acudiente son obligatorios (solo dígitos en el documento).")
            else:
                ts = datetime.now().isoformat(timespec="seconds")
                row = [
                    ts, "TRUE" if es_mayor else "FALSE", tipo_doc_p, doc_p.strip(), nombre.strip(), apodo.strip(),
                    tel.strip(), correo.strip(), str(fecha_nac), "",
                    eps.strip(), rest_alim.strip(), salud_mental.strip(), region.strip(), obra.strip(), proceso.strip(),
                    ", ".join(intereses), exp_sig.strip(), dato_freak.strip(), pregunta.strip(),
                    int(ranks["Servicio"]), int(ranks["Peregrinaje"]), int(ranks["Cultura y arte"]),
                    int(ranks["Espiritualidad"]), int(ranks["Vocación"]), int(ranks["Incidencia política"]),
                    "",  # experiencia_top_calculada
                    perfil_cerc, motivo.strip(), preguntas_frec.strip(),
                    acomp_viv.strip(), "TRUE" if acomp_esp else "FALSE", "TRUE" if acomp_psico else "FALSE", "TRUE" if acomp_esc else "FALSE",
                    {"Sí":"Si","No":"No","Más o menos":"Mas o menos"}[conoce_rji],
                    tipo_doc_a, doc_a.strip(), nom_a.strip(), correo_a.strip(), tel_a.strip(),
                    "TRUE" if acepta_datos else "FALSE"
                ]
                try:
                    append_row(EXCEL_PATH, "PARTICIPANTES", row, PARTICIPANTES_COLS)
                    try: update_unificado(EXCEL_PATH)
                    except Exception: pass
                    st.success("Participante guardado.")
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

# ================= ACOMPAÑANTE =================
with tab2:
    with st.form("form_acompanante", clear_on_submit=False):
        st.markdown("#### Datos personales del acompañante / acudiente")
        tipo_doc_ac = st.selectbox("Tipo de documento", ["CC","CE","Pasaporte","Otro"])
        doc_ac = st.text_input("Documento (solo dígitos)", max_chars=20, placeholder="Ej: 1012345678")
        nom_ac = st.text_input("Nombre completo")
        correo_ac = st.text_input("Correo")
        tel_ac = st.text_input("Teléfono")
        organiz = st.text_input("Organización (si aplica)")
        region_ac = st.text_input("Región")
        rol = st.text_input("Rol en la organización (si aplica)")
        trae_varios = st.radio("¿Trae varios jóvenes?", ["Sí","No"], horizontal=True) == "Sí"
        exp_acomp = st.selectbox("¿A qué experiencia acompaña?", ["Servicio","Peregrinaje","Cultura y arte","Espiritualidad","Vocación","Incidencia política"])

        st.markdown("#### Logística Medellín")
        ciudad_origen = st.text_input("Ciudad de origen del grupo")
        hora_llegada = st.time_input("¿A qué hora llegará el grupo a Medellín?", value=time(14, 0))

        st.markdown("#### Consentimiento y relación de menores")
        archivo = st.file_uploader("Sube el archivo (PDF/Excel/Imagen) con la lista firmada de menores", type=["pdf","xlsx","xls","csv","png","jpg","jpeg"])
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

                row = [
                    ts, tipo_doc_ac, doc_ac.strip(), nom_ac.strip(), correo_ac.strip(), tel_ac.strip(),
                    organiz.strip(), region_ac.strip(), rol.strip(),
                    "TRUE" if trae_varios else "FALSE",
                    exp_acomp, ciudad_origen.strip(), hora_llegada.strftime("%H:%M"),
                    save_url, lista_texto.strip()
                ]
                try:
                    append_row(EXCEL_PATH, "ACOMPANANTES", row, ACOMPANANTES_COLS)
                    try: update_unificado(EXCEL_PATH)
                    except Exception: pass
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
