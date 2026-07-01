import contextlib
import io
import json
import re
import shutil
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import streamlit as st
from buscar_maps import agregar_prospecto_desde_maps_url, buscar_prospectos, generar_busquedas
from crm_utils import ARCHIVO_EXCEL, CLIENTES_DEFAULT, NICHOS, PLANTILLA_DEFAULT, ZONAS, asegurar_excel, guardar_excel, normalizar_telefono
from project_factory import crear_proyecto_cliente, finalizar_proyecto
from visual_analyzer import analizar_perfil_visual

CONFIG_PATH = Path("config.json")
EXPORT_DIR = Path("exports")

DEFAULT_CONFIG = {
    "ruta_plantilla_react": PLANTILLA_DEFAULT,
    "ruta_carpeta_clientes": CLIENTES_DEFAULT,
    "usuario_github": "",
    "configuracion_vercel": "",
}

COLUMNAS_VISIBLES = [
    "Prioridad", "Puntaje_Prioridad", "Motivo_Prioridad", "Tiene_web", "Sitio_web", "Resenas",
    "ID", "Nombre", "Nicho", "Telefono", "Rating", "Direccion", "Horario", "Categoria", "Estado",
    "Ultimo_Contacto", "Proximo_Seguimiento", "Persona_Contacto", "Canal", "Probabilidad_Cierre",
    "Valor_Estimado", "Historial_Comercial", "Demo", "Repositorio_GitHub", "Vercel_URL",
    "Google_Maps", "WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp", "Notas", "Fecha_busqueda",
]

ESTADOS_PIPELINE = [
    "Nuevo", "Contactado", "Respondió", "Interesado", "Demo enviada",
    "Negociación", "Cliente", "Perdido", "Pospuesto",
]

ESTADOS_EQUIVALENTES = {"Pendiente": "Nuevo", "Demo creada": "Demo enviada", "Demo publicada": "Demo enviada", "Cerrado": "Cliente", "Cotización enviada": "Negociación"}





def extraer_telefono_valido(telefono):
    """Extrae un teléfono mexicano válido de textos largos o celdas sucias."""
    if pd.isna(telefono):
        return ""

    texto = str(telefono)
    patrones = [
        r"(?<!\d)(?:\+?52|0052)\s*(?:\(?\d{2,3}\)?[\s.\-]*)?\d{3,4}[\s.\-]*\d{4}(?!\d)",
        r"(?<!\d)(?:\(?\d{2,3}\)?[\s.\-]*)?\d{3,4}[\s.\-]*\d{4}(?!\d)",
    ]

    for patron in patrones:
        for coincidencia in re.finditer(patron, texto):
            digitos = normalizar_telefono(coincidencia.group(0))
            if digitos.startswith("00"):
                digitos = digitos[2:]
            if len(digitos) == 13 and digitos.startswith("521"):
                return f"52{digitos[-10:]}"
            if len(digitos) == 12 and digitos.startswith("52"):
                return digitos
            if len(digitos) == 10:
                return digitos

    digitos = normalizar_telefono(telefono)
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) == 13 and digitos.startswith("521"):
        return f"52{digitos[-10:]}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return digitos
    if len(digitos) == 10:
        return digitos
    return ""


def telefono_para_mostrar(telefono):
    """Devuelve el teléfono limpio para UI o un aviso cuando no hay número válido."""
    digitos = extraer_telefono_valido(telefono)
    if not digitos:
        return "Sin teléfono válido"
    numero = digitos[-10:]
    telefono_formateado = f"{numero[:2]} {numero[2:6]} {numero[6:]}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return f"+52 {telefono_formateado}"
    return telefono_formateado


def normalizar_telefono_whatsapp(telefono):
    """Devuelve un teléfono mexicano en formato internacional para WhatsApp."""
    digitos = extraer_telefono_valido(telefono)
    if not digitos:
        return ""
    if len(digitos) == 10:
        return f"52{digitos}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return digitos
    return ""


def crear_link_whatsapp_web(telefono):
    numero = normalizar_telefono_whatsapp(telefono)
    return f"https://wa.me/{numero}" if numero else ""


def url_whatsapp(telefono):
    return crear_link_whatsapp_web(telefono)


def marcar_whatsapp_manual(df, idx, whatsapp, estado, nota="", error=""):
    df.at[idx, "WhatsApp"] = whatsapp
    df.at[idx, "Fecha_Verificacion_WhatsApp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    df.at[idx, "Estado"] = estado
    df.at[idx, "Error_WhatsApp"] = error
    if nota:
        notas_actuales = str(df.at[idx, "Notas"] or "").strip() if "Notas" in df.columns else ""
        if nota not in notas_actuales:
            df.at[idx, "Notas"] = f"{notas_actuales}; {nota}" if notas_actuales else nota
    guardar_excel(df, ARCHIVO_EXCEL)


def estado_crm(valor):
    estado = str(valor or "").strip()
    return ESTADOS_EQUIVALENTES.get(estado, estado or "Nuevo")


def has_value(value):
    return bool(str(value or "").strip())


def row_value(row, column, default=""):
    value = row.get(column, default) if hasattr(row, "get") else default
    return "" if pd.isna(value) else value


def parse_date(value):
    if pd.isna(value) or not str(value).strip():
        return None
    parsed = pd.to_datetime(value, errors="coerce")
    return None if pd.isna(parsed) else parsed.date()


def save_cell(df, idx, column, value, note=None):
    df.at[idx, column] = value
    if note:
        previous = str(df.at[idx, "Historial_Comercial"] or "") if "Historial_Comercial" in df.columns else ""
        stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        df.at[idx, "Historial_Comercial"] = f"{previous}\n[{stamp}] {note}".strip()
    guardar_excel(df, ARCHIVO_EXCEL)


def action_button(label, key, callback, *args, **kwargs):
    if st.button(label, key=key, **kwargs):
        callback(*args)
        st.success("Cambio guardado inmediatamente.")
        st.rerun()


def prospect_card(row, idx, df, prefix):
    nombre = row_value(row, "Nombre", "Sin nombre")
    st.markdown(f"**{nombre}**")
    st.caption(f"{row_value(row, 'Prioridad')} · ⭐ {row_value(row, 'Rating')} · {row_value(row, 'Resenas')} reseñas")
    st.write(f"📞 {row_value(row, 'Telefono') or 'Sin teléfono'}")
    st.write(f"🌐 Web: {row_value(row, 'Tiene_web') or 'no'} | Estado: {estado_crm(row_value(row, 'Estado'))}")
    st.write(f"Último: {row_value(row, 'Ultimo_Contacto') or '—'}")
    st.write(f"Próximo: {row_value(row, 'Proximo_Seguimiento') or '—'}")
    b1, b2 = st.columns(2)
    with b1:
        maps = row_value(row, "Google_Maps")
        if maps: st.link_button("Maps", maps, use_container_width=True)
        action_button("+3 días", f"{prefix}_3", save_cell, df, idx, "Proximo_Seguimiento", (date.today()+timedelta(days=3)).isoformat(), "Seguimiento programado en 3 días")
        action_button("Contactado", f"{prefix}_contactado", save_cell, df, idx, "Estado", "Contactado", "Marcado como Contactado")
    with b2:
        repo = row_value(row, "Repositorio_GitHub") or row_value(row, "URL_GitHub")
        vercel = row_value(row, "Vercel_URL") or row_value(row, "URL_Vercel")
        if repo: st.link_button("GitHub", repo, use_container_width=True)
        elif vercel: st.link_button("Vercel", vercel, use_container_width=True)
        action_button("+7 días", f"{prefix}_7", save_cell, df, idx, "Proximo_Seguimiento", (date.today()+timedelta(days=7)).isoformat(), "Seguimiento programado en 7 días")
        action_button("Interesado", f"{prefix}_interesado", save_cell, df, idx, "Estado", "Interesado", "Marcado como Interesado")
    with st.expander("Más acciones"):
        st.caption("Acciones de proyecto")
        p1, p2 = st.columns(2)
        with p1:
            if st.button("Crear proyecto", key=f"{prefix}_crear"):
                with st.spinner("Creando proyecto..."):
                    crear_proyecto_cliente(row_value(row, "ID"))
                st.rerun()
        with p2:
            if st.button("Finalizar proyecto", key=f"{prefix}_finalizar"):
                with st.spinner("Finalizando proyecto..."):
                    finalizar_proyecto(row_value(row, "ID"))
                st.rerun()
        st.caption("Cambios rápidos de estado")
        quick_cols = st.columns(3)
        for pos, quick_estado in enumerate(["Respondió", "Demo enviada", "Negociación", "Cliente", "Perdido"]):
            with quick_cols[pos % 3]:
                action_button(quick_estado, f"{prefix}_quick_{quick_estado}", save_cell, df, idx, "Estado", quick_estado, f"Marcado como {quick_estado}")
        estado = st.selectbox("Cambiar estado", ESTADOS_PIPELINE, index=ESTADOS_PIPELINE.index(estado_crm(row_value(row, "Estado"))) if estado_crm(row_value(row, "Estado")) in ESTADOS_PIPELINE else 0, key=f"{prefix}_estado")
        action_button("Guardar estado", f"{prefix}_guardar_estado", save_cell, df, idx, "Estado", estado, f"Estado cambiado a {estado}")
        nota = st.text_input("Nota rápida", key=f"{prefix}_nota")
        if st.button("Agregar nota", key=f"{prefix}_agregar_nota") and nota.strip():
            previous = str(row_value(row, "Notas"))
            save_cell(df, idx, "Notas", f"{previous}\n{datetime.now():%Y-%m-%d}: {nota}".strip(), f"Nota rápida: {nota}")
            st.rerun()
        wa = url_whatsapp(row_value(row, "Telefono"))
        if wa: st.code(wa, language=None)


def render_metrics(df):
    metricas = [("Total prospectos", len(df)), ("Nuevos", sum(estado_crm(x)=="Nuevo" for x in df.get("Estado", []))),
        ("Contactados", sum(estado_crm(x)=="Contactado" for x in df.get("Estado", []))), ("Respondieron", sum(estado_crm(x)=="Respondió" for x in df.get("Estado", []))),
        ("Interesados", sum(estado_crm(x)=="Interesado" for x in df.get("Estado", []))), ("Demo enviada", sum(estado_crm(x)=="Demo enviada" for x in df.get("Estado", []))),
        ("Negociación", sum(estado_crm(x)=="Negociación" for x in df.get("Estado", []))), ("Clientes", sum(estado_crm(x)=="Cliente" for x in df.get("Estado", []))),
        ("Perdidos", sum(estado_crm(x)=="Perdido" for x in df.get("Estado", []))), ("Demos creadas", metric_count(df, "Proyecto_Creado", "sí") + df.get("Demo", pd.Series(dtype=str)).fillna("").astype(str).ne("").sum()),
        ("Repositorios", metric_count(df, "Repo_Creado", "sí") + df.get("Repositorio_GitHub", pd.Series(dtype=str)).fillna("").astype(str).ne("").sum()), ("Deploys", metric_count(df, "Deploy_Completado", "sí") + df.get("Vercel_URL", pd.Series(dtype=str)).fillna("").astype(str).ne("").sum())]
    for row in [metricas[:6], metricas[6:]]:
        for col, (label, value) in zip(st.columns(6), row):
            col.metric(label, int(value))


def ordenar_columnas_clave(df):
    primeras = [col for col in COLUMNAS_VISIBLES if col in df.columns]
    restantes = [col for col in df.columns if col not in primeras]
    return df[primeras + restantes]


def load_config():
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            return {**DEFAULT_CONFIG, **data}
        except json.JSONDecodeError:
            st.warning("config.json no es válido. Se muestran valores por defecto.")
    return DEFAULT_CONFIG.copy()


def save_config(config):
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_prospectos():
    return asegurar_excel(ARCHIVO_EXCEL)


def normalize_list(text):
    return [item.strip() for item in str(text or "").split(",") if item.strip()]


def yes_no_filter(df, column, value):
    if value == "Todos" or column not in df.columns:
        return df
    return df[df[column].fillna("").astype(str).str.lower().isin({value.lower(), value.lower().replace("í", "i")})]


def metric_count(df, column, expected):
    if column not in df.columns:
        return 0
    return int(df[column].fillna("").astype(str).str.lower().eq(expected.lower()).sum())


def apply_filters(df, prioridad, estado, tiene_web, nicho):
    filtered = df.copy()
    if prioridad != "Todas" and "Prioridad" in filtered.columns:
        filtered = filtered[filtered["Prioridad"].fillna("").astype(str).str.lower() == prioridad.lower()]
    if estado != "Todos" and "Estado" in filtered.columns:
        filtered = filtered[filtered["Estado"].fillna("").astype(str) == estado]
    filtered = yes_no_filter(filtered, "Tiene_web", tiene_web)
    if nicho != "Todos" and "Nicho" in filtered.columns:
        filtered = filtered[filtered["Nicho"].fillna("").astype(str) == nicho]
    return filtered


def export_excel(df, name):
    EXPORT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = EXPORT_DIR / f"{name}_{timestamp}.xlsx"
    df = df.copy()
    if "Resenas" not in df.columns:
        df["Resenas"] = 0
    df["Resenas"] = pd.to_numeric(df["Resenas"], errors="coerce").fillna(0).astype(int)
    ordenar_columnas_clave(df).to_excel(path, index=False)
    return path


st.set_page_config(page_title="CRM Restaurantes", page_icon="🍽️", layout="wide")
st.title("CRM Restaurantes")

section = st.sidebar.radio(
    "Secciones",
    ["Dashboard", "Buscar prospectos", "Agregar por Google Maps", "Ver prospectos", "Verificar WhatsApp", "Crear proyecto", "Finalizar proyecto", "Exportar", "Configuración"],
)

if section == "Dashboard":
    st.header("Dashboard de ventas")
    df = load_prospectos()
    render_metrics(df)

    st.subheader("Hoy qué hago")
    today = date.today()
    acciones = []
    for idx, row in df.iterrows():
        estado = estado_crm(row_value(row, "Estado"))
        proximo = parse_date(row_value(row, "Proximo_Seguimiento"))
        nombre = row_value(row, "Nombre", "Sin nombre")
        if proximo and proximo <= today:
            acciones.append((1, idx, nombre, f"Seguimiento vencido o para hoy ({proximo.isoformat()})"))
        if estado == "Interesado" and not proximo:
            acciones.append((2, idx, nombre, "Interesado sin próximo seguimiento"))
        if has_value(row_value(row, "Demo")) and estado != "Demo enviada":
            acciones.append((3, idx, nombre, "Demo creada sin enviar"))
        if estado == "Respondió" and not proximo:
            acciones.append((4, idx, nombre, "Respondió y falta definir siguiente paso"))
        if estado == "Negociación":
            acciones.append((5, idx, nombre, "Negociación abierta"))
    acciones = sorted(acciones, key=lambda item: item[0])
    if acciones:
        for prioridad_accion, idx, nombre, motivo in acciones[:25]:
            with st.expander(f"{prioridad_accion}. {nombre} — {motivo}"):
                prospect_card(df.loc[idx], idx, df, f"today_{idx}_{prioridad_accion}")
    else:
        st.success("No hay seguimientos vencidos ni acciones críticas para hoy.")

    st.subheader("Pipeline visual")
    pipe_cols = st.columns(len(ESTADOS_PIPELINE))
    for col, estado in zip(pipe_cols, ESTADOS_PIPELINE):
        subset = df[df.get("Estado", pd.Series(dtype=str)).apply(estado_crm) == estado] if not df.empty else df
        with col:
            st.metric(estado, len(subset))
            for idx, row in subset.head(4).iterrows():
                with st.container(border=True):
                    prospect_card(row, idx, df, f"pipe_{estado}_{idx}")
            if len(subset) > 4:
                st.caption(f"+ {len(subset) - 4} más")

    st.subheader("Buscador y filtros")
    filtered = df.copy()
    search = st.text_input("Buscar prospectos", "")
    if search:
        filtered = filtered[filtered.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)]
    f1, f2, f3, f4 = st.columns(4)
    estado = f1.selectbox("Estado", ["Todos"] + ESTADOS_PIPELINE)
    prioridad = f2.selectbox("Prioridad", ["Todas", "Alta", "Media", "Baja"])
    nichos = ["Todos"] + sorted([x for x in df.get("Nicho", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
    nicho = f3.selectbox("Nicho", nichos)
    tiene_web = f4.selectbox("Tiene web", ["Todos", "sí", "no"])
    f5, f6, f7, f8 = st.columns(4)
    demo = f5.selectbox("Demo creada", ["Todos", "Sí", "No"])
    repo = f6.selectbox("Repo creado", ["Todos", "Sí", "No"])
    deploy = f7.selectbox("Deploy", ["Todos", "Sí", "No"])
    vencido = f8.checkbox("Seguimiento vencido")
    r1, r2 = st.columns(2)
    rating_range = r1.slider("Rango de rating", 0.0, 5.0, (0.0, 5.0), 0.1)
    resenas_range = r2.slider("Rango de reseñas", 0, int(max(1000, pd.to_numeric(df.get("Resenas", pd.Series([0])), errors="coerce").fillna(0).max() if not df.empty else 1000)), (0, int(max(1000, pd.to_numeric(df.get("Resenas", pd.Series([0])), errors="coerce").fillna(0).max() if not df.empty else 1000))))
    if estado != "Todos": filtered = filtered[filtered["Estado"].apply(estado_crm) == estado]
    if prioridad != "Todas": filtered = filtered[filtered["Prioridad"].fillna("").astype(str) == prioridad]
    if nicho != "Todos": filtered = filtered[filtered["Nicho"].fillna("").astype(str) == nicho]
    filtered = yes_no_filter(filtered, "Tiene_web", tiene_web)
    for label, column, choice in [("demo", "Demo", demo), ("repo", "Repositorio_GitHub", repo), ("deploy", "Vercel_URL", deploy)]:
        if choice != "Todos":
            mask = filtered[column].fillna("").astype(str).ne("") if column in filtered else pd.Series(False, index=filtered.index)
            filtered = filtered[mask if choice == "Sí" else ~mask]
    if vencido:
        filtered = filtered[filtered["Proximo_Seguimiento"].apply(lambda value: (parse_date(value) or date.max) <= today)]
    ratings = pd.to_numeric(filtered.get("Rating", pd.Series(dtype=float)), errors="coerce").fillna(0)
    resenas = pd.to_numeric(filtered.get("Resenas", pd.Series(dtype=int)), errors="coerce").fillna(0)
    filtered = filtered[ratings.between(*rating_range) & resenas.between(*resenas_range)]

    st.subheader("Vista detalle")
    if filtered.empty:
        st.info("No hay prospectos con los filtros actuales.")
    else:
        options = [f"{row.ID} - {row.Nombre}" for row in filtered[["ID", "Nombre"]].itertuples(index=False)]
        selected = st.selectbox("Seleccionar prospecto", options)
        selected_id = selected.split(" - ", 1)[0]
        idx = df[df["ID"].astype(str) == str(selected_id)].index[0]
        row = df.loc[idx]
        c1, c2 = st.columns([1, 1])
        with c1:
            st.write({k: row_value(row, k) for k in ["Nombre", "Telefono", "Direccion", "Google_Maps", "Rating", "Resenas", "Sitio_web", "Prioridad", "Motivo_Prioridad", "Estado", "Demo", "Repositorio_GitHub", "Vercel_URL"]})
        with c2:
            with st.form(f"detalle_{idx}"):
                new_estado = st.selectbox("Estado", ESTADOS_PIPELINE, index=ESTADOS_PIPELINE.index(estado_crm(row_value(row, "Estado"))) if estado_crm(row_value(row, "Estado")) in ESTADOS_PIPELINE else 0)
                notas = st.text_area("Notas", str(row_value(row, "Notas")))
                ultimo = st.date_input("Fecha último contacto", value=parse_date(row_value(row, "Ultimo_Contacto")) or today)
                proximo = st.date_input("Fecha próximo seguimiento", value=parse_date(row_value(row, "Proximo_Seguimiento")) or today)
                persona = st.text_input("Persona de contacto", str(row_value(row, "Persona_Contacto")))
                canal = st.text_input("Canal", str(row_value(row, "Canal")))
                prob = st.number_input("Probabilidad de cierre (%)", 0, 100, int(float(row_value(row, "Probabilidad_Cierre") or 0)))
                valor = st.number_input("Valor estimado", min_value=0.0, value=float(row_value(row, "Valor_Estimado") or 0), step=100.0)
                if st.form_submit_button("Guardar detalle", type="primary"):
                    for col_name, val in {"Estado": new_estado, "Notas": notas, "Ultimo_Contacto": ultimo.isoformat(), "Proximo_Seguimiento": proximo.isoformat(), "Persona_Contacto": persona, "Canal": canal, "Probabilidad_Cierre": prob, "Valor_Estimado": valor}.items():
                        df.at[idx, col_name] = val
                    save_cell(df, idx, "Historial_Comercial", row_value(row, "Historial_Comercial"), "Detalle actualizado")
                    st.rerun()
            st.text_area("Historial comercial", str(row_value(row, "Historial_Comercial")), disabled=True)

    st.subheader("Tabla secundaria")
    st.caption(f"Mostrando {len(filtered)} de {len(df)} prospectos")
    st.dataframe(ordenar_columnas_clave(filtered), use_container_width=True, hide_index=True)

elif section == "Buscar prospectos":
    st.header("Buscar prospectos")
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        nichos_txt = st.text_area("Nichos", value=", ".join(NICHOS), help="Separados por coma")
    with col2:
        zonas_txt = st.text_area("Zonas", value=", ".join(ZONAS), help="Separadas por coma")
    with col3:
        maximo = st.number_input("Máximo por búsqueda", min_value=1, max_value=200, value=40, step=1)
        headless = st.checkbox("Modo invisible", value=True)

    if st.button("Buscar nuevos prospectos", type="primary"):
        nichos = normalize_list(nichos_txt) or NICHOS
        zonas = normalize_list(zonas_txt) or ZONAS
        busquedas = generar_busquedas(nichos, zonas)
        progress = st.progress(0, text="Iniciando búsqueda...")
        output = io.StringIO()
        before = len(load_prospectos())
        try:
            progress.progress(10, text=f"Ejecutando {len(busquedas)} búsquedas en Google Maps...")
            with st.spinner("Buscando prospectos. Esto puede tardar varios minutos..."):
                with contextlib.redirect_stdout(output):
                    buscar_prospectos(busquedas=busquedas, max_por_busqueda=int(maximo), headless=headless, archivo=ARCHIVO_EXCEL)
            progress.progress(100, text="Búsqueda finalizada")
            after_df = load_prospectos()
            st.success(f"Búsqueda terminada. Registros antes: {before}. Registros ahora: {len(after_df)}.")
            st.dataframe(ordenar_columnas_clave(after_df.tail(20)), use_container_width=True)
        except Exception as exc:
            progress.progress(100, text="Búsqueda interrumpida")
            st.error(f"No se pudo completar la búsqueda: {exc}")
        with st.expander("Ver detalle de ejecución"):
            st.code(output.getvalue() or "Sin salida de consola.")

elif section == "Agregar por Google Maps":
    st.header("Agregar prospecto por link de Google Maps")
    maps_url = st.text_input("Link de Google Maps", placeholder="https://maps.app.goo.gl/... o https://www.google.com/maps/place/...")
    col1, col2 = st.columns([1, 1])
    with col1:
        headless_link = st.checkbox("Modo invisible", value=True, key="maps_link_headless")
    with col2:
        actualizar_faltantes = st.checkbox("Actualizar datos faltantes si ya existe", value=False)

    if st.button("Agregar prospecto por link", type="primary"):
        if not maps_url.strip():
            st.warning("Pega un link de Google Maps para continuar.")
        else:
            before = len(load_prospectos())
            try:
                with st.spinner("Abriendo Google Maps y extrayendo datos del negocio..."):
                    resultado = agregar_prospecto_desde_maps_url(
                        maps_url,
                        archivo=ARCHIVO_EXCEL,
                        headless=headless_link,
                        actualizar_faltantes=actualizar_faltantes,
                    )
                registro = resultado.get("registro", {})
                if resultado.get("nuevo"):
                    st.success(f"Prospecto nuevo guardado con ID {resultado.get('id')}.")
                elif resultado.get("actualizado"):
                    st.info(f"Este prospecto ya existe. ID {resultado.get('id')}. Se actualizaron datos faltantes.")
                else:
                    st.info(f"Este prospecto ya existe. ID {resultado.get('id')}.")

                st.subheader("Resumen")
                st.write({
                    "Nombre": registro.get("Nombre", ""),
                    "Teléfono": registro.get("Telefono", ""),
                    "Web": registro.get("Tiene_web", ""),
                    "Rating": registro.get("Rating", ""),
                    "Reseñas": registro.get("Resenas", ""),
                    "Prioridad": registro.get("Prioridad", ""),
                    "Puntaje_Prioridad": registro.get("Puntaje_Prioridad", ""),
                    "Motivo_Prioridad": registro.get("Motivo_Prioridad", ""),
                    "Sitio_web": registro.get("Sitio_web", ""),
                    "Dirección": registro.get("Direccion", ""),
                })
                after_df = load_prospectos()
                st.caption(f"Registros antes: {before}. Registros ahora: {len(after_df)}.")
            except Exception as exc:
                st.error(f"No se pudo agregar el prospecto desde Google Maps: {exc}")

elif section == "Ver prospectos":
    st.header("Ver prospectos")
    df = load_prospectos()
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("Total prospectos", len(df))
    m2.metric("Alta prioridad", metric_count(df, "Prioridad", "Alta"))
    m3.metric("Sin página web", metric_count(df, "Tiene_web", "no"))
    m4.metric("Contactados", metric_count(df, "Estado", "Contactado"))
    m5.metric("Interesados", metric_count(df, "Estado", "Interesado"))
    m6.metric("Cerrados", metric_count(df, "Estado", "Cerrado"))

    f1, f2, f3, f4 = st.columns(4)
    prioridad = f1.selectbox("Prioridad", ["Todas", "Alta", "Media", "Baja"])
    estados = ["Todos"] + sorted([x for x in df.get("Estado", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
    estado = f2.selectbox("Estado", estados)
    tiene_web = f3.selectbox("Tiene web", ["Todos", "sí", "no"])
    nichos = ["Todos"] + sorted([x for x in df.get("Nicho", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
    nicho = f4.selectbox("Nicho", nichos)

    filtered = apply_filters(df, prioridad, estado, tiene_web, nicho)
    st.caption(f"Mostrando {len(filtered)} de {len(df)} prospectos")
    st.dataframe(ordenar_columnas_clave(filtered), use_container_width=True, hide_index=True)

elif section == "Verificar WhatsApp":
    st.header("Verificación manual de WhatsApp")
    st.warning("No se envían mensajes automáticamente y no se intenta detectar WhatsApp automáticamente.")
    st.caption("Flujo manual asistido: abre un enlace wa.me para que una persona revise el número. El Excel solo se actualiza cuando presionas Sí tiene WhatsApp, No tiene WhatsApp o Revisar después.")

    df = load_prospectos()
    for columna in ["WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp", "Notas", "Estado", "Telefono", "Prioridad", "Nicho"]:
        if columna not in df.columns:
            df[columna] = ""
    df["WhatsApp"] = df["WhatsApp"].fillna("").replace("", "Pendiente").astype(str)

    wa = df["WhatsApp"]
    c1, c2, c3 = st.columns(3)
    c1.metric("WhatsApp pendientes", int(wa.str.lower().eq("pendiente").sum()))
    c2.metric("WhatsApp Sí", int(wa.eq("Sí").sum()))
    c3.metric("WhatsApp No", int(wa.eq("No").sum()))

    f1, f2, f3, f4 = st.columns(4)
    prioridad_sel = f1.selectbox("Prioridad", ["Todas", "Alta", "Media", "Baja"])
    estados_disponibles = ["Todos"] + sorted([x for x in df.get("Estado", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
    estado_sel = f2.selectbox("Estado", estados_disponibles)
    nichos_disponibles = ["Todos"] + sorted([x for x in df.get("Nicho", pd.Series(dtype=str)).dropna().astype(str).unique() if x])
    nicho_sel = f3.selectbox("Nicho", nichos_disponibles)
    cantidad_mostrar = f4.number_input("Cantidad a mostrar", min_value=1, max_value=100, value=20, step=1)

    if st.button("Limpiar teléfonos del Excel"):
        backup_path = Path("prospectos_restaurantes_backup.xlsx")
        shutil.copy2(ARCHIVO_EXCEL, backup_path)
        telefonos_limpios = df["Telefono"].apply(telefono_para_mostrar)
        mascara_validos = telefonos_limpios.ne("Sin teléfono válido")
        total_limpiados = int((df.loc[mascara_validos, "Telefono"].astype(str) != telefonos_limpios[mascara_validos].astype(str)).sum())
        df.loc[mascara_validos, "Telefono"] = telefonos_limpios[mascara_validos]
        guardar_excel(df, ARCHIVO_EXCEL)
        st.success(f"Respaldo creado en {backup_path} y {total_limpiados} teléfonos limpiados en el Excel.")
        st.rerun()

    candidatos = df.copy()
    candidatos = candidatos[candidatos["WhatsApp"].fillna("Pendiente").replace("", "Pendiente").astype(str).str.lower() == "pendiente"]
    candidatos = candidatos[candidatos["Telefono"].fillna("").astype(str).str.strip().ne("")]
    if prioridad_sel != "Todas":
        candidatos = candidatos[candidatos["Prioridad"].fillna("").astype(str).str.lower() == prioridad_sel.lower()]
    if estado_sel != "Todos":
        candidatos = candidatos[candidatos["Estado"].fillna("").astype(str) == estado_sel]
    if nicho_sel != "Todos":
        candidatos = candidatos[candidatos["Nicho"].fillna("").astype(str) == nicho_sel]

    candidatos_mostrar = candidatos.head(int(cantidad_mostrar))
    columnas_wa = ["ID", "Nombre", "Telefono", "WhatsApp", "Estado"]
    st.subheader("Prospectos para revisión manual")
    st.caption(f"Mostrando {len(candidatos_mostrar)} de {len(candidatos)} prospectos filtrados por WhatsApp = Pendiente y con teléfono.")
    if candidatos_mostrar.empty:
        st.warning("No hay prospectos que coincidan con los filtros")
    else:
        tabla_manual = candidatos_mostrar[[c for c in columnas_wa if c in candidatos_mostrar.columns]].copy()
        if "Telefono" in tabla_manual.columns:
            tabla_manual["Telefono"] = tabla_manual["Telefono"].apply(telefono_para_mostrar)
        st.dataframe(tabla_manual, use_container_width=True, hide_index=True)

    for idx, row in candidatos_mostrar.iterrows():
        nombre = row_value(row, "Nombre", "Sin nombre")
        telefono = row_value(row, "Telefono")
        estado_actual = row_value(row, "Estado")
        telefono_limpio = telefono_para_mostrar(telefono)
        telefono_normalizado = normalizar_telefono_whatsapp(telefono)
        wa_web_url = crear_link_whatsapp_web(telefono)
        with st.container(border=True):
            st.markdown(f"**ID:** {row_value(row, 'ID', '—')}")
            st.markdown(f"**Nombre:** {nombre}")
            st.write(f"📞 {telefono_limpio}")
            if not telefono_normalizado:
                st.caption("No se detectó teléfono válido")

            b1, b2, b3, b4 = st.columns(4)
            with b1:
                if wa_web_url:
                    st.link_button("Abrir WhatsApp", wa_web_url)
                else:
                    st.button("Abrir WhatsApp", key=f"wa_open_disabled_{idx}", disabled=True)
            with b2:
                if st.button("Sí tiene WhatsApp", key=f"wa_si_{idx}"):
                    marcar_whatsapp_manual(df, idx, "Sí", "WhatsApp verificado")
                    st.success("WhatsApp marcado como Sí, estado actualizado y Excel guardado.")
                    st.rerun()
            with b3:
                if st.button("No tiene WhatsApp", key=f"wa_no_{idx}"):
                    marcar_whatsapp_manual(df, idx, "No", "Sin WhatsApp")
                    st.success("WhatsApp marcado como No, estado actualizado y Excel guardado.")
                    st.rerun()
            with b4:
                if st.button("Revisar después", key=f"wa_revisar_{idx}"):
                    marcar_whatsapp_manual(df, idx, "Pendiente", estado_actual or "Nuevo", nota="Revisar WhatsApp después")
                    st.success("Prospecto marcado para revisar WhatsApp después y Excel guardado.")
                    st.rerun()

elif section == "Crear proyecto":
    st.header("Crear proyecto del cliente")
    df = load_prospectos()
    if df.empty:
        st.info("No hay prospectos guardados todavía.")
    else:
        options = [f"{row.ID} - {row.Nombre}" for row in df[["ID", "Nombre"]].itertuples(index=False)]
        selected = st.selectbox("Selector de prospecto por ID o nombre", options)
        id_prospecto = selected.split(" - ", 1)[0]
        prospecto_preview = df[df["ID"].astype(str) == str(id_prospecto)]
        if not prospecto_preview.empty:
            with st.expander("Perfil visual que se incluirá en restaurant.json y codex_task.md"):
                st.json(analizar_perfil_visual(prospecto_preview.iloc[0].to_dict()))

        if st.button("Crear proyecto", type="primary"):
            with st.spinner("Creando carpeta, archivos Codex, repo GitHub y push..."):
                resumen = crear_proyecto_cliente(id_prospecto)
            if resumen:
                st.success("Proyecto listo. Seleccione el repositorio en Codex y pegue la tarea.")
                st.write("**Ruta local:**", resumen.get("carpeta") or "")
                st.write("**Repo GitHub:**", resumen.get("github") or "")
                st.write("**URL Vercel:**", resumen.get("vercel") or "")
                st.write("**Archivo codex_task.md:**", resumen.get("codex_task") or "")
            else:
                st.error("No se pudo generar la demo completa. Revisa la consola o las notas del prospecto.")

elif section == "Finalizar proyecto":
    st.header("Finalizar proyecto")
    df = load_prospectos()
    if df.empty:
        st.info("No hay prospectos guardados todavía.")
    else:
        options = [f"{row.ID} - {row.Nombre}" for row in df[["ID", "Nombre"]].itertuples(index=False)]
        selected = st.selectbox("Selector de prospecto", options)
        id_prospecto = selected.split(" - ", 1)[0]
        if st.button("Finalizar proyecto", type="primary"):
            with st.spinner("Ejecutando git pull, npm install, build y deploy Vercel..."):
                resumen = finalizar_proyecto(id_prospecto)
            if resumen:
                st.success("Proyecto finalizado.")
                st.write("**Repositorio:**", resumen.get("repositorio") or "")
                st.write("**Vercel:**", resumen.get("vercel") or "")
                st.write("**Ruta local:**", resumen.get("ruta") or "")
            else:
                st.error("No se pudo finalizar el proyecto.")

elif section == "Exportar":
    st.header("Exportar")
    df = load_prospectos()
    exports = {
        "Todos": df,
        "Prioridad Alta": df[df["Prioridad"].fillna("").astype(str).str.lower() == "alta"] if "Prioridad" in df else df.iloc[0:0],
        "Sin página web": df[df["Tiene_web"].fillna("").astype(str).str.lower().isin(["no", ""])] if "Tiene_web" in df else df.iloc[0:0],
        "Contactados": df[df["Estado"].fillna("").astype(str).str.lower() == "contactado"] if "Estado" in df else df.iloc[0:0],
    }
    for label, data in exports.items():
        if st.button(f"Exportar {label}"):
            path = export_excel(data, label.lower().replace(" ", "_"))
            st.success(f"Excel guardado: {path} ({len(data)} registros)")

elif section == "Configuración":
    st.header("Configuración")
    config = load_config()
    with st.form("config_form"):
        config["ruta_plantilla_react"] = st.text_input("Ruta de plantilla React", config["ruta_plantilla_react"])
        config["ruta_carpeta_clientes"] = st.text_input("Ruta de carpeta Clientes", config["ruta_carpeta_clientes"])
        config["usuario_github"] = st.text_input("Usuario GitHub", config["usuario_github"])
        config["configuracion_vercel"] = st.text_area("Configuración Vercel", config["configuracion_vercel"])
        if st.form_submit_button("Guardar configuración", type="primary"):
            save_config(config)
            st.success(f"Configuración guardada en {CONFIG_PATH}")
