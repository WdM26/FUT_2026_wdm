import streamlit as st
import datetime
import pytz
import qrcode
import base64
import os
from io import BytesIO
from xhtml2pdf import pisa

# --- 1. CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="FUT UNSCH v.2", page_icon="🎓", layout="wide")

# Función para cargar el CSS con codificación explícita
def local_css(file_name):
    if os.path.exists(file_name):
        with open(file_name, encoding="utf-8") as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Llamar a la función de estilos
local_css("style.css")

# Inicialización de estados
vars_control = ['f_nom', 'f_dni', 'f_cod', 'f_cel', 'f_cor', 'f_ir', 'f_ia']
for v in vars_control:
    if v not in st.session_state: st.session_state[v] = ""

# --- FUNCIONES DE UTILIDAD ---
def get_image_base64(path):
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"
    return ""

def get_qr_base64(text):
    qr = qrcode.QRCode(box_size=10, border=1)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = BytesIO()
    img.save(buf, format="PNG")
    return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode()}"

def build_html(d):
    try:
        # 1. Leer el archivo con codificación correcta
        with open("template.html", "r", encoding="utf-8") as f:
            template = f.read()

        if 'doc_list' in d:
            # Convertimos \n a <br> para que el PDF entienda el salto
            lista_con_saltos = str(d['doc_list']).replace("\n", "<br>")
            # Lo inyectamos directamente en el template para saltarnos el paso 8
            template = template.replace("{d['doc_list']}", lista_con_saltos)
            template = template.replace('{d["doc_list"]}', lista_con_saltos)

        # 2. Limpieza de seguridad: Convertir Nones en vacíos
        for key in d:
            if d[key] is None:
                d[key] = ""

                     
        # 4. Preparar el diccionario de reemplazos directos
        reemplazos = {
            "{logo_full}": get_image_base64("logo_fut.jpg"),
            "{mod_final}": d.get('mod_final', ""),
            "{f_fundamento}": d.get('fundamento', ""),
            "{qr}": d.get('qr', "")
        }

        # 5. Ejecutar reemplazos de variables especiales y logo
        for key, val in reemplazos.items():
            template = template.replace(key, str(val))

        # 6. Reemplazo de los datos tipo {d['campo']}
        for key, value in d.items():
            # CRÍTICO: Si la llave es doc_list, NO la reemplaces aquí 
            # porque ya la inyectamos arriba con los <br>
            if key == 'doc_list':
                continue 
                
            template = template.replace(f"{{d['{key}']}}", str(value))
            template = template.replace(f"{{d[\"{key}\"]}}", str(value))

        # 7. Lógica para los checks {chk(...)} usando Regex
        import re
        def replace_chk(match):
            campo = match.group(1)
            esperado = match.group(2)
            return "<b>[X]</b>" if str(d.get(campo)) == str(esperado) else "[&nbsp;&nbsp;]"

        template = re.sub(r"\{chk\(d\['(.*?)'\],'(.*?)'\)\}", replace_chk, template)

        # 8. Limpieza de saltos de línea del CÓDIGO HTML
        template = template.replace("\n", "").replace("\r", "").strip()

        # 9. REEMPLAZO FINAL (Hazlo AQUÍ para que no lo borre el paso 8)
        # Esto inyecta los <br> justo antes de crear el PDF
        lista_html = str(d.get('doc_list', "")).replace("\n", "<br>")
        template = template.replace("{d['doc_list']}", lista_html)
        template = template.replace('{d["doc_list"]}', lista_html)

        return template

    except FileNotFoundError:
        st.error("❌ No se encontró el archivo template.html")
        return ""
    except Exception as e:
        st.error(f"❌ Error al procesar el HTML: {e}")
        return ""

# --- DATA MAESTRA (Cuadros Seleccionables) ---
DATA_ACADEMICA = {
    "ADMINISTRACIÓN DE EMPRESAS": {"grado": ["CIENCIAS ADMINISTRATIVAS"], "facultad": "CIENCIAS ECONÓMICAS, ADMINISTRATIVAS Y CONTABLES", "escuela": "ADMINISTRACIÓN DE EMPRESAS"},
    "AGRONOMÍA": {"grado": ["CIENCIAS AGRÍCOLAS"], "facultad": "CIENCIAS AGRARIAS", "escuela": "AGRONOMÍA"},
    "CIENCIA, FISICO MATEMATICO": {"grado": ["MATEMÁTICAS", "FÍSICA", "ESTADÍSTICA"], "facultad": "INGENIERÍA DE MINAS, GEOLOGÍA Y CIVIL", "escuela": "CIENCIA, FISICO MATEMATICO"},
    "CONTABILIDAD Y AUDITORÍA": {"grado": ["CIENCIAS CONTABLES"], "facultad": "CIENCIAS ECONÓMICAS, ADMINISTRATIVAS Y CONTABLES", "escuela": "CONTABILIDAD Y AUDITORÍA"},
    "ECONOMÍA": {"grado": ["ECONOMÍA"], "facultad": "CIENCIAS ECONÓMICAS, ADMINISTRATIVAS Y CONTABLES", "escuela": "ECONOMÍA"},
    "INGENIERÍA AGRÍCOLA": {"grado": ["CIENCIAS AGRÍCOLAS"], "facultad": "CIENCIAS AGRARIAS", "escuela": "INGENIERÍA AGRÍCOLA"},
    "INGENIERÍA AGROFORESTAL": {"grado": ["CIENCIAS AGROFORESTALES"], "facultad": "CIENCIAS AGRARIAS", "escuela": "INGENIERÍA AGROFORESTAL"},
    "INGENIERÍA AGROINDUSTRIAL": {"grado": ["INGENIERÍA AGROINDUSTRIAL"], "facultad": "CIENCIAS AGRARIAS", "escuela": "INGENIERÍA AGROINDUSTRIAL"},
    "INGENIERÍA CIVIL": {"grado": ["CIENCIAS DE LA INGENIERÍA CIVIL"], "facultad": "INGENIERÍA DE MINAS, GEOLOGÍA Y CIVIL", "escuela": "INGENIERÍA CIVIL"},
    "INGENIERÍA DE MINAS": {"grado": ["CIENCIAS DE LA INGENIERÍA DE MINAS"], "facultad": "INGENIERÍA DE MINAS, GEOLOGÍA Y CIVIL", "escuela": "INGENIERÍA DE MINAS"},
    "INGENIERÍA DE SISTEMAS": {"grado": ["INGENIERÍA DE SISTEMAS"], "facultad": "INGENIERÍA DE MINAS, GEOLOGÍA Y CIVIL", "escuela": "INGENIERÍA DE SISTEMAS"},
    "INGENIERÍA EN INDUSTRIAS ALIMENTARIAS": {"grado": ["INGENIERÍA EN INDUSTRIAS ALIMENTARIAS"], "facultad": "INGENIERÍA QUÍMICA Y METALURGIA", "escuela": "INGENIERÍA EN INDUSTRIAS ALIMENTARIAS"},
    "INGENIERÍA QUÍMICA": {"grado": ["INGENIERÍA QUÍMICA"], "facultad": "INGENIERÍA QUÍMICA Y METALURGIA", "escuela": "INGENIERÍA QUÍMICA"},
    "ARQUITECTURA": {"grado": ["CIENCIAS DE LA ARQUITECTURA"], "facultad": "INGENIERÍA DE MINAS, GEOLOGÍA Y CIVIL", "escuela": "ARQUITECTURA"},
    "INGENIERÍA AMBIENTAL": {"grado": ["INGENIERÍA AMBIENTAL"], "facultad": "INGENIERÍA DE MINAS, GEOLOGÍA Y CIVIL", "escuela": "INGENIERÍA AMBIENTAL"},
    "ANTROPOLOGÍA SOCIAL": {"grado": ["CIENCIA SOCIAL: ANTROPOLOGÍA SOCIAL"], "facultad": "CIENCIAS SOCIALES", "escuela": "ANTROPOLOGÍA SOCIAL"},
    "ARQUEOLOGÍA E HISTORIA": {"grado": ["CIENCIA SOCIAL: ARQUEOLOGÍA", "CIENCIA SOCIAL: HISTORIA"], "facultad": "CIENCIAS SOCIALES", "escuela": "ARQUEOLOGÍA E HISTORIA"},
    "CIENCIAS DE LA COMUNICACIÓN": {"grado": ["CIENCIAS DE LA COMUNICACIÓN"], "facultad": "CIENCIAS SOCIALES", "escuela": "CIENCIAS DE LA COMUNICACIÓN"},
    "DERECHO": {"grado": ["DERECHO"], "facultad": "DERECHO Y CIENCIAS POLÍTICAS", "escuela": "DERECHO"},
    "EDUCACIÓN FÍSICA": {"grado": ["CIENCIAS DE LA EDUCACIÓN"], "facultad": "CIENCIAS DE LA EDUCACIÓN", "escuela": "EDUCACIÓN FÍSICA"},
    "EDUCACIÓN INICIAL": {"grado": ["CIENCIAS DE LA EDUCACIÓN"], "facultad": "CIENCIAS DE LA EDUCACIÓN", "escuela": "EDUCACIÓN INICIAL"},
    "EDUCACIÓN PRIMARIA": {"grado": ["CIENCIAS DE LA EDUCACIÓN"], "facultad": "CIENCIAS DE LA EDUCACIÓN", "escuela": "EDUCACIÓN PRIMARIA"},
    "EDUCACIÓN SECUNDARIA": {"grado": ["CIENCIAS DE LA EDUCACIÓN"], "facultad": "CIENCIAS DE LA EDUCACIÓN", "escuela": "EDUCACIÓN SECUNDARIA"},
    "TRABAJO SOCIAL": {"grado": ["CIENCIA SOCIAL: TRABAJO SOCIAL"], "facultad": "CIENCIAS SOCIALES", "escuela": "TRABAJO SOCIAL"},
    "BIOLOGÍA": {"grado": ["CIENCIAS BIOLÓGICAS"], "facultad": "CIENCIAS BIOLÓGICAS", "escuela": "BIOLOGÍA"},
    "ENFERMERÍA": {"grado": ["CIENCIAS DE LA ENFERMERÍA"], "facultad": "CIENCIAS DE LA SALUD", "escuela": "ENFERMERÍA"},
    "FARMACIA Y BIOQUÍMICA": {"grado": ["FARMACIA Y BIOQUÍMICA"], "facultad": "CIENCIAS DE LA SALUD", "escuela": "FARMACIA Y BIOQUÍMICA"},
    "MEDICINA HUMANA": {"grado": ["MEDICINA HUMANA"], "facultad": "CIENCIAS DE LA SALUD", "escuela": "MEDICINA HUMANA"},
    "OBSTETRICIA": {"grado": ["OBSTETRICIA"], "facultad": "CIENCIAS DE LA SALUD", "escuela": "OBSTETRICIA"},
    "PSICOLOGÍA": {"grado": ["PSICOLOGÍA"], "facultad": "CIENCIAS DE LA SALUD", "escuela": "PSICOLOGÍA"}
}

PUEBLOS = [
    "QUECHUAS", "ACHUAR", "AIMARA", "AMAHUACA", "ARABELA", "ASHANINKA", 
    "ASHENINKA", "AWAJÚN", "BORA", "CASHINAHUA", "CHAMICURO", "CHAPRA", 
    "CHITONAHUA", "ESE EJA", "HARAKBUT", "IKITU", "IÑAPARI", "ISKONAWA", 
    "JAQARU", "JÍBARO", "KAKATAIBO", "KAKINTE", "KANDOZI", "KAPANAWA", 
    "KICHWA", "KUKAMA KUKAMIRIA", "MADIJA", "MAIJUNA", "MARINAHUA", 
    "MASHCO PIRO", "MASTANAHUA", "MATSÉS", "MATSIGENKA", "MUNICHE", 
    "MURUI-MUINANƗ", "NAHUA", "NANTI", "NOMATSIGENGA", "OCAINA", "OMAGUA", 
    "RESÍGARO", "SECOYA", "SHARANAHUA", "SHAWI", "SHIPIBO-KONIBO", 
    "SHIWILU", "TICUNA", "URARINA", "URO", "VACACOCHA", "WAMPIS", 
    "YAGUA", "YAMINAHUA", "YANESHA", "YINE"]

OPCIONES_AFRO = ["AFROPERUANO", "OTRO"]

LENGUAS = [
    "QUECHUA", "ACHUAR", "AIMARA", "AMAHUACA", "ARABELA", "ASHANINKA", 
    "ASHENINKA", "AWAJÚN", "BORA", "CASHINAHUA", "CHAMIKURO", "ESE EJA", 
    "HARAKBUT", "IKITU", "IÑAPARI", "ISKONAWA", "JAQARU", "KAKATAIBO", 
    "KAKINTE", "KANDOZI-CHAPRA", "KAPANAWA", "KAWKI", "KUKAMA KUKAMIRIA", 
    "MADIJA", "MAIJƗKI", "MATSÉS", "MATSIGENKA", "MATSIGENKA MONTETOKUNIRIRA", 
    "MUNICHI", "MURUI-MUINANƗ", "NAHUA", "NOMATSIGENGA", "OCAINA", "OMAGUA", 
    "RESÍGARO", "SECOYA", "SHARANAHUA", "SHAWI", "SHIPIBO-KONIBO", "SHIWILU", 
    "TAUSHIRO", "TICUNA", "URARINA", "WAMPIS", "YAGUA", "YAMINAHUA", 
    "YANESHA", "YINE", "CASTELLANO", "OTRO"]

OPCIONES_INGRESO_UNSCH = [
    "ORDINARIO", 
    "ADJUDICADO - CEPRE UNSCH",
    "PRIMEROS Y SEGUNDOS PUESTOS EN SECUNDARIA (RURAL)",
    "PRIMEROS Y SEGUNDOS PUESTOS EN SECUNDARIA (URBANO)",
    "TRASLADO INTERNO",
    "TRASLADO EXTERNO NACIONAL",
    "TRASLADO EXTERNO EXTRAORDINARIO: DE UNIVERSIDADES NO LICENCIADAS",
    "TRASLADO INTERNACIONAL",
    "VÍCTIMAS DE TERRORISMO O VIOLENCIA SOCIOPOLÍTICA",
    "DEPORTISTAS CALIFICADOS SEGÚN LEY N° 28036",
    "PERSONAS CON DISCAPACIDAD",
    "INTEGRANTES DE LOS PUEBLOS ANDINOS",
    "GRADUADOS Y/O TITULADOS DE NIVEL UNIVERSITARIO",
    "TRASLADO EXTERNO INTERNACIONAL",
    "INTEGRANTES DE LOS PUEBLOS AMAZONICOS",
    "COAR / BACHILLERATO INTERNACIONAL",
    "SOCIO POLITICO Y VICT. TERRORISMO (RURAL)",
    "SOCIO POLITICO Y VICT. TERRORISMO (URBANO)",
    "TALENTOS ESPECIALES / CONVENIOS",
    "OTRO"
]

# Definimos quiénes NO llevan el prefijo EXONERADO
MODALIDADES_DIRECTAS = ["ORDINARIO", "ADJUDICADO - CEPRE UNSCH"]

# --- 1. ENCABEZADO Y TÍTULO (FUERA DEL CONTENEDOR PARA EVITAR CUADROS) ---
logo_data = get_image_base64("logo_fut.jpg")
if logo_data:
    st.markdown(f"""
        <div class="header-fix">
            <img src="{logo_data}" class="logo-header">
            <a href="/" target="_self" class="btn-nueva-solicitud">NUEVA SOLICITUD</a>
        </div>
    """, unsafe_allow_html=True)

st.markdown('<div class="titulo-principal"><h2>FUT UNSCH - GRADO BACHILLER</h2></div>', unsafe_allow_html=True)




# --- 2. CONTENIDO DEL FORMULARIO ---
# Eliminamos 'border=True' del container principal para que el CSS gestione las tarjetas individuales
with st.container(border=True):
    # IMPORTANTE: El título debe estar AQUÍ ADENTRO para que el borde lo rodee
    # SECCIÓN 1: DESTINO Y GRADO (UNIFICADO EN UNA SOLA TARJETA)
    st.markdown("### 🏛️ DESTINO Y GRADO")
    
    c1, c2 = st.columns(2)
    
    with c1:
        f_esc_dir = st.selectbox(
            "Señor Director de la E.P. de:", 
            list(DATA_ACADEMICA.keys()),
            key="sb_escuela",
            help="Seleccione la Facultad que corresponde a su carrera." # Esto genera el icono (i)
        )
    
    # Lógica de datos para la UNSCH
    info_auto = DATA_ACADEMICA[f_esc_dir]
    opciones_grado = info_auto["grado"]
    
    with c2:
        if len(opciones_grado) > 1:
            f_gra = st.selectbox(
                "Grado Académico Solicitado:", 
                opciones_grado,
                key="sb_grado",
                help="Seleccione el título que desea obtener." # Esto genera el icono (i)
            )
        else:
            f_gra = st.selectbox(
                "Grado Académico Solicitado:", 
                opciones_grado, 
                disabled=True, 
                help="Seleccionado automáticamente según la Dirección de Escuela Profesional.",
                key="sb_grado_dis"
            )
    # SECCIÓN 2: DATOS DEL SOLICITANTE
    st.markdown("### 👤 DATOS DEL SOLICITANTE")
    col31, col32 = st.columns([3, 1])
    f_nom = col31.text_input("Apellidos y Nombres (DNI)").upper()
    f_dni = col32.text_input("DNI", max_chars=8)
    
    col61, col62, col63 = st.columns(3)
    f_cel = col61.text_input("Celular")
    f_dir = col62.text_input("Dirección", placeholder="Ej: Urb. Los Olivos - Ayacucho")
    f_cor = col63.text_input("Correo Electrónico")

    # SECCIÓN 3: INFORMACIÓN ACADÉMICA
    st.markdown("### 🎓 INFORMACIÓN ACADÉMICA")
    st.markdown(f"""
        <div style="border-left: 5px solid #7a1212; padding: 12px 15px; background-color: #fffafb; border-radius: 4px; margin-bottom: 20px;">
            <div style="color: #7a1212; font-weight: bold; font-size: 0.9em; margin-bottom: 4px;">📍 DETECCIÓN AUTOMÁTICA:</div>
            <div style="color: #333; font-size: 0.95em;">
                <b>Facultad:</b> {info_auto['facultad']}<br><b>Escuela:</b> {info_auto['escuela']}
            </div>
        </div>
    """, unsafe_allow_html=True)
    
    f_mba = st.radio("Modalidad de Grado de Bachiller:", ["Automático", "Curso de Trabajo de Investigacion"], horizontal=True)

    h1, h2, h3, h4 = st.columns([1, 1, 2, 2])
    f_cod = h1.text_input("Código Estudiante:", placeholder="Ej: 20214520")
    f_ia = h2.text_input("Año Ingreso:", placeholder="Ej: 2020-II")

    # Usamos la constante definida arriba
    f_im = h3.selectbox("Modalidad Ingreso", OPCIONES_INGRESO_UNSCH)

    # Lógica de formateo para el PDF
    if f_im in MODALIDADES_DIRECTAS:
        mod_final_pdf = f_im
    else:
        mod_final_pdf = f"EXONERADO - {f_im}"

    f_ir = h4.text_input("Resolución de Ingreso", placeholder="Ej: RCU N° 2452-2021-UNSCH-2021")
    
    f_d1, f_d2, f_d3, f_d4 = st.columns(4)
    v_mf = f_d1.text_input("F. 1ra Mat.")
    v_ms = f_d2.text_input("Sem. 1ra")
    v_ef = f_d3.text_input("F. Egreso")
    v_es = f_d4.text_input("Sem. Egreso")

    # SECCIÓN 4: INFORMACIÓN ÉTNICA
    st.markdown("### 🌍 INFORMACIÓN ÉTNICA")
    et1, et2 = st.columns(2)
    with et1:
        f_etc = st.radio("¿Pertenencia Étnica?", ["No", "Indigina u uriginaria", "Afroperuana", "NS"], horizontal=True)
        opciones_pueblo = PUEBLOS if f_etc == "Indigina u uriginaria" else (["AFROPERUANO", "OTRO"] if f_etc == "Afroperuana" else ["N/A"])
        f_ete = st.selectbox("Especifique Pueblo/Etnia:", opciones_pueblo, disabled=(f_etc in ["No", "NS"]))

    with et2:
        f_lec = st.radio("¿Habla lengua originaria?", ["No", "Si", "NS"], horizontal=True)
        opciones_lengua = [l for l in LENGUAS if l != "CASTELLANO"] if f_lec == "Si" else ["N/A"]
        f_lee = st.selectbox("Especifique Lengua:", opciones_lengua, disabled=(f_lec != "Si"))

    # SECCIÓN 5: FUNDAMENTO
    st.markdown("### ✍️ FUNDAMENTO DE LA SOLICITUD")
    plantilla_fundamento = f"Habiendo culminado satisfactoriamente mis estudios superiores en la Escuela Profesional de {info_auto['escuela']}, conforme al plan de estudios 2004, recurro a su digno despacho para que se sirva disponer se me otorgue el grado académico de Bachiller en {f_gra}, motivo por el cual adjunto los requisitos exigidos para su atención oportuna."
    
    if "edit_fund" not in st.session_state: st.session_state.edit_fund = False
    
    f_fundamento = st.text_area("Cuerpo del fundamento:", value=st.session_state.get("fundamento_final", plantilla_fundamento), 
                                height=150, disabled=not st.session_state.edit_fund, key="txt_fund", label_visibility="collapsed")
    st.session_state["fundamento_final"] = f_fundamento

    col_v1, col_v2, col_v3 = st.columns([2, 1, 1]) 
    with col_v3:
        lbl_f = "✅ GUARDAR" if st.session_state.edit_fund else "🔓 EDITAR"
        if st.button(lbl_f, key="btn_f_dinamico", use_container_width=True, type="secondary"):
            st.session_state.edit_fund = not st.session_state.edit_fund
            st.rerun()

    # SECCIÓN 6: DOCUMENTOS ADJUNTOS
    st.markdown("### 📁 DOCUMENTOS ADJUNTOS")

    # Definir la lista completa hasta la h
    docs_nuevos = (
        "a) Solicitud.\n"
        "b) Recibo de pago por derecho de grado académico de bachiller.\n"
        "c) Copia simple de DNI.\n"
        "d) Dos (02) fotografías pasaporte.\n"
        "e) Copia simple de Certificado de Estudios.\n"
        "f) Declaración jurada de no adeudar a la Facultad, Dirección de Bienestar Universitario y Unidad de Biblioteca.\n"
        "g) Declaración jurada de no tener antecedentes judiciales y penales segun reglamento de Grados y Títulos.\n"
        "h) Otros Segun Reglamento de grados titulos.\n"
    )

    if "edit_docs" not in st.session_state: 
        st.session_state.edit_docs = False

    # Usamos txt_docs como key principal
    f_docs_raw = st.text_area(
        "Lista de documentos:", 
        value=st.session_state.get("mis_docs", docs_nuevos), 
        height=220, # Aumentado para que se vea hasta la 'h' sin scroll
        disabled=not st.session_state.edit_docs, 
        key="txt_docs", 
        label_visibility="collapsed"
    )
    st.session_state["mis_docs"] = f_docs_raw

    col_d1, col_d2, col_d3 = st.columns([2, 1, 1])
    with col_d3:
        lbl_d = "✅ GUARDAR" if st.session_state.edit_docs else "🔓 EDITAR"
        if st.button(lbl_d, key="btn_d", use_container_width=True, type="secondary"):
            st.session_state.edit_docs = not st.session_state.edit_docs
            st.rerun()

    # SECCIÓN 7: UBICACIÓN Y FECHA
    st.markdown("### 📍 UBICACIÓN Y FECHA")
    col_lug, col_fec = st.columns(2)
    
    with col_lug:
        # Aquí asignamos "Ayacucho" como valor automático
        f_lug = st.text_input("Lugar", value="Ayacucho") 
        
    with col_fec:
        tz_peru = pytz.timezone('America/Lima')
        f_fec_obj = st.date_input("Seleccione Fecha", value=datetime.datetime.now(tz_peru).date())
        
        meses_es = {
            1: "enero", 2: "febrero", 3: "marzo", 4: "abril", 5: "mayo", 6: "junio", 
            7: "julio", 8: "agosto", 9: "septiembre", 10: "octubre", 11: "noviembre", 12: "diciembre"
        }
        f_fec = f"{f_fec_obj.day} de {meses_es[f_fec_obj.month]} de {f_fec_obj.year}"

    # BOTÓN DE GENERACIÓN FINAL
    if st.button("🚀 GENERAR FUT", use_container_width=True, type="primary"):
        # 1. Validación de campos obligatorios
        campos_obligatorios = {
            "Apellidos y Nombres": f_nom,
            "DNI": f_dni,
            "Código de Estudiante": f_cod,
            "Año de Ingreso": f_ia,
            "Celular": f_cel,
            "Dirección": f_dir,
            "Correo Electrónico": f_cor
        }

        faltantes = [nombre for nombre, valor in campos_obligatorios.items() if not valor or str(valor).strip() == ""]

        if faltantes:
            st.error(f"⚠️ **Atención:** Falta completar: {', '.join(faltantes)}.")
        
        elif len(f_dni) != 8:
            st.warning("⚠️ El DNI debe tener exactamente 8 caracteres.")

        # Verificar que no estén editando el fundamento o documentos
        elif st.session_state.get("edit_fund") or st.session_state.get("edit_docs"):
            st.info("💡 Por favor, pulsa '✅ GUARDAR' en Fundamento o Documentos antes de generar.")

        else:
            with st.spinner("⏳ Generando documento para la UNSCH..."):
                try:
                    # Preparar datos para el PDF
                    data_pdf = {
                        "esc_dir": f_esc_dir,
                        "grado": f_gra,
                        "nombre": f_nom.upper(),
                        "dni": f_dni,
                        "facultad": info_auto["facultad"],
                        "escuela": info_auto["escuela"],
                        "m_bach": f_mba,
                        "cod": f_cod,
                        "i_a": f_ia,
                        "mod_final": mod_final_pdf,
                        "i_r": f_ir.upper() if f_ir else "---",
                        "m_f": v_mf, "m_s": v_ms, "e_f": v_ef, "e_s": v_es,
                        "cel": f_cel, "dir": f_dir, "cor": f_cor,
                        "lugar": f_lug if f_lug else "Ayacucho",
                        "fecha": f_fec,
                        "fundamento": st.session_state.get("fundamento_final", ""),
                        "doc_list": st.session_state.get("txt_docs", docs_nuevos),
                        "et_c": f_etc,
                        "et_e": f_ete if f_etc in ["Indigina u uriginaria", "Afroperuana"] else "---",
                        "le_c": f_lec,
                        "le_e": f_lee if f_lec == "Si" else "---",
                        "qr": get_qr_base64(f"FUT-UNSCH|{f_dni}|{f_nom}|{f_fec}")
                    }

                    # Crear PDF
                    html_content = build_html(data_pdf)
                    pdf_out = BytesIO()
                    pisa_status = pisa.CreatePDF(
                        BytesIO(html_content.encode("UTF-8")),
                        dest=pdf_out,
                        encoding='utf-8'
                    )

                    if not pisa_status.err:
                        st.session_state.pdf_final = pdf_out.getvalue()
                        st.success("✅ ¡Documento generado con éxito! Haz clic en el botón de abajo para descargar.")
                    else:
                        st.error("❌ Error técnico al crear la estructura del PDF.")

                except Exception as e:
                    st.error(f"❌ Error inesperado: {e}")

        # SECCIÓN DE DESCARGA
        if 'pdf_final' in st.session_state:
            st.markdown("---")
            st.download_button(
                label="📥 DESCARGAR FUT COMPLETADO (PDF)",
                data=st.session_state.pdf_final,
                file_name=f"FUT_{f_dni}.pdf",
                mime="application/pdf",
                use_container_width=True
            )