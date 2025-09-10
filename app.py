import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
from utils import (
    ensure_excel_with_sheets, append_row, update_unificado,
    PARTICIPANTES_COLS, ACOMPANANTES_COLS, UNIFICADO_COLS,
)

st.set_page_config(page_title="Claveriado RJI · Inscripción", page_icon="🌊", layout="centered")

# --- Estilos globales (dark) ---
st.markdown(
    """
    <style>
    :root {
      --card-radius: 18px;
    }
    .main {background-color: #111827;} /* gris oscuro */
    .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 980px;}
    .rji-card {
        background: #1f2937; /* gris más claro para tarjetas */
        padding: 1.25rem 1.5rem;
        border-radius: var(--card-radius);
        border: 1px solid #374151;
        box-shadow: 0 12px 30px rgba(0,0,0,0.4);
    }
    .rji-title {font-size: 2rem; font-weight: 800; margin: .2rem 0 .2rem; color: #f9fafb;}
    .rji-sub {color: #9ca3af; margin-bottom: 1.2rem; font-size: 0.95rem;}
    .rji-badge {display:inline-block; padding: .2rem .55rem; border-radius: 999px;
                background:#374151; color:#facc15; font-weight:600; font-size:.78rem;}
    .stTabs [data-baseweb="tab-list"] {gap: 6px;}
    .stTabs [data-baseweb="tab"] {
        background: #1f2937; 
        border-radius: 999px; 
        padding: .4rem .9rem; 
        border:1px solid #374151; 
        color: #f3f4f6;
    }
    .stTabs [aria-selected="true"] {
        border:1px solid #facc15; 
        background: #292f3d; 
        color: #facc15;
    }
    label, .stTextInput>div>div>input, .stTextArea textarea, .stSelectbox div, .stRadio div {
        color: #f9fafb !important;
    }
    .stTextInput>div>div>input, .stTextArea textarea {
        background-color: #111827 !important;
    }
    .stSelectbox>div>div>div {
        background-color: #111827 !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Sidebar
with st.sidebar:
    st.image("assets/logo.png", caption="RJI", use_column_width=True)
    st.markdown("### Archivo de datos")
    default_path = Path("rji_datos.xlsx")
    excel_path = st.text_input(
        "Ruta del archivo Excel (se creará si no existe):",
        value=str(default_path),
        help="Puedes poner una ruta absoluta o dejar el nombre por defecto."
    )
    excel_path = Path(excel_path).expanduser()
    ensure_excel_with_sheets(excel_path)
    st.caption(f"Usando: `{excel_path}`")
    st.divider()
    st.markdown("### 🔗 Utilidades")
    if st.button(" Actualizar hoja UNIFICADO", use_container_width=True):
        try:
            n = update_unificado(excel_path)
            st.success(f"UNIFICADO actualizado con {n} filas.")
        except Exception as e:
            st.error(f"Error al actualizar UNIFICADO: {e}")
    st.caption("Este botón cruza participantes con acompañantes y valida consentimientos.")

# Header
st.markdown('<div class="rji-card">', unsafe_allow_html=True)
st.markdown('<span class="rji-badge">Inscripciones</span>', unsafe_allow_html=True)
st.markdown('<div class="rji-title">RJI</div>', unsafe_allow_html=True)
st.markdown('<div class="rji-sub">Participantes y Acompañantes</div>', unsafe_allow_html=True)

# Tabs
tab1, tab2 = st.tabs(["Participante", "Acompañante/Acudiente"])

# ------------------ PARTICIPANTE ------------------
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
        fecha_nac = st.date_input("Fecha de nacimiento")
        eps = st.text_input("EPS", placeholder="Escribe tu EPS")
        rest_alim = st.text_input("Restricciones alimentarias (o 'ninguna')", placeholder="Vegetariano, alergias, etc.")
        salud_mental = st.text_area("Salud mental (observaciones/alertas)", placeholder="Información que debamos conocer para cuidarte mejor.")
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
        intereses = st.multiselect("Intereses personales", ["Aventura","Deporte","Contemplación","Arte","Mascotas","Tecnología","Naturaleza","Lectura"])
        dato_freak = st.text_input("Dato freak de ti", placeholder="Algo curioso sobre ti")
        ola = st.text_input("¿Cuál es la ola más grande a la que te has enfrentado?")
        pregunta = st.text_input("Propón una pregunta para conectar con otros")

        st.markdown("#### Experiencias")
        st.caption("Ordena de mayor a menor interés (1 = quiero con locura, 6 = no quiero nada)")
        ranks = {}
        col1, col2 = st.columns(2)
        with col1:
            ranks["Servicio"] = st.number_input("Servicio (1-6)", 1, 6, 1, step=1)
            ranks["Peregrinaje"] = st.number_input("Peregrinaje (1-6)", 1, 6, 2, step=1)
            ranks["Cultura y arte"] = st.number_input("Cultura y arte (1-6)", 1, 6, 3, step=1)
        with col2:
            ranks["Espiritualidad"] = st.number_input("Espiritualidad (1-6)", 1, 6, 4, step=1)
            ranks["Vocación"] = st.number_input("Vocación (1-6)", 1, 6, 5, step=1)
            ranks["Incidencia política"] = st.number_input("Incidencia política (1-6)", 1, 6, 6, step=1)

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

        enviado = st.form_submit_button("Guardar participante ✨", use_container_width=True)
        if enviado:
            if not doc_p.strip().isdigit():
                st.error("El documento del participante debe contener solo dígitos.")
            elif (not es_mayor) and (not doc_a.strip().isdigit() or not nom_a.strip()):
                st.error("Para menores, el documento y nombre del acudiente son obligatorios (solo dígitos en el documento).")
            else:
                ts = datetime.now().isoformat(timespec="seconds")
                row = [
                    ts,
                    "TRUE" if es_mayor else "FALSE",
                    tipo_doc_p,
                    doc_p.strip(),
                    nombre.strip(),
                    apodo.strip(),
                    tel.strip(),
                    correo.strip(),
                    str(fecha_nac),
                    eps.strip(),
                    rest_alim.strip(),
                    salud_mental.strip(),
                    region.strip(),
                    obra.strip(),
                    proceso.strip(),
                    exp_sig.strip(),
                    ", ".join(intereses),
                    dato_freak.strip(),
                    ola.strip(),
                    pregunta.strip(),
                    int(ranks["Servicio"]),
                    int(ranks["Peregrinaje"]),
                    int(ranks["Cultura y arte"]),
                    int(ranks["Espiritualidad"]),
                    int(ranks["Vocación"]),
                    int(ranks["Incidencia política"]),
                    perfil_cerc,
                    motivo.strip(),
                    preguntas_frec.strip(),
                    acomp_viv.strip(),
                    "TRUE" if acomp_esp else "FALSE",
                    "TRUE" if acomp_psico else "FALSE",
                    "TRUE" if acomp_esc else "FALSE",
                    {"Sí":"Si","No":"No","Más o menos":"Mas o menos"}[conoce_rji],
                    tipo_doc_a,
                    doc_a.strip(),
                    nom_a.strip(),
                    correo_a.strip(),
                    tel_a.strip(),
                ]
                try:
                    append_row(excel_path, "PARTICIPANTES", row, PARTICIPANTES_COLS)
                    st.success("¡Participante guardado!")
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

# ------------------ ACOMPANANTE ------------------
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

        st.markdown("#### Consentimiento y relación de menores")
        archivo = st.file_uploader("Sube el archivo (PDF/Excel/Imagen) con la lista firmada de menores", type=["pdf","xlsx","xls","csv","png","jpg","jpeg"])
        st.caption("Consejo: además del archivo, puedes escribir abajo los documentos para validar automáticamente.")
        lista_texto = st.text_area("(Opcional) Escribe los documentos de los menores separados por coma")

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
                    exp_acomp, save_url, lista_texto.strip()
                ]
                try:
                    append_row(excel_path, "ACOMPANANTES", row, ACOMPANANTES_COLS)
                    st.success("¡Acompañante guardado!")
                except Exception as e:
                    st.error(f"No se pudo guardar: {e}")

st.markdown("</div>", unsafe_allow_html=True)
