import contextlib
import io
import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from buscar_maps import agregar_prospecto_desde_maps_url, buscar_prospectos, generar_busquedas
from crm_utils import ARCHIVO_EXCEL, CLIENTES_DEFAULT, NICHOS, PLANTILLA_DEFAULT, ZONAS, asegurar_excel
from project_factory import crear_proyecto_cliente, finalizar_proyecto

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
    "Demo", "Repositorio_GitHub", "Vercel_URL", "Google_Maps", "Notas", "Fecha_busqueda",
]


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
    ["Dashboard", "Buscar prospectos", "Agregar por Google Maps", "Ver prospectos", "Crear proyecto", "Finalizar proyecto", "Exportar", "Configuración"],
)

if section == "Dashboard":
    st.header("Dashboard")
    df = load_prospectos()
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total prospectos", len(df))
    c2.metric("Alta prioridad", metric_count(df, "Prioridad", "Alta"))
    c3.metric("Interesados", metric_count(df, "Estado", "Interesado"))
    c4.metric("Demos creadas", metric_count(df, "Proyecto_Creado", "sí"))
    c5.metric("Repositorios", metric_count(df, "Repo_Creado", "sí"))
    c6.metric("Deploys", metric_count(df, "Deploy_Completado", "sí"))
    search = st.text_input("Buscador", "")
    base = df.copy()
    if search:
        mask = base.astype(str).apply(lambda col: col.str.contains(search, case=False, na=False)).any(axis=1)
        base = base[mask]
    st.dataframe(ordenar_columnas_clave(base), use_container_width=True, hide_index=True)

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

elif section == "Crear proyecto":
    st.header("Crear proyecto del cliente")
    df = load_prospectos()
    if df.empty:
        st.info("No hay prospectos guardados todavía.")
    else:
        options = [f"{row.ID} - {row.Nombre}" for row in df[["ID", "Nombre"]].itertuples(index=False)]
        selected = st.selectbox("Selector de prospecto por ID o nombre", options)
        id_prospecto = selected.split(" - ", 1)[0]
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
