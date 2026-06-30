import random
import re
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from crm_utils import ARCHIVO_EXCEL, asegurar_excel, guardar_excel, normalizar_telefono

WHATSAPP_SI = "Sí"
WHATSAPP_NO = "No"
WHATSAPP_ERROR = "Error"
WHATSAPP_PENDIENTE = "Pendiente"
PERFIL_WHATSAPP = Path(".whatsapp_profile")


def normalizar_telefono_whatsapp(telefono):
    """Devuelve teléfono en formato internacional para WhatsApp Web.

    Por defecto asume México: 10 dígitos locales => 52XXXXXXXXXX.
    """
    digitos = normalizar_telefono(telefono)
    if not digitos:
        return ""
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if digitos.startswith("+"):
        digitos = digitos[1:]
    if len(digitos) == 10:
        return f"52{digitos}"
    if len(digitos) == 11 and digitos.startswith("1"):
        return f"52{digitos[-10:]}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return digitos
    if len(digitos) == 13 and digitos.startswith("521"):
        return f"52{digitos[-10:]}"
    return digitos


def _asegurar_columnas_whatsapp(df):
    for columna in ["WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp"]:
        if columna not in df.columns:
            df[columna] = ""
    df["WhatsApp"] = df["WhatsApp"].fillna("").replace("", WHATSAPP_PENDIENTE)
    return df


def _sesion_whatsapp():
    playwright = sync_playwright().start()
    context = playwright.chromium.launch_persistent_context(
        str(PERFIL_WHATSAPP), headless=False, viewport={"width": 1280, "height": 900}
    )
    page = context.pages[0] if context.pages else context.new_page()
    page.goto("https://web.whatsapp.com/", wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector("div[contenteditable='true'][role='textbox'], canvas[aria-label*='Scan'], canvas", timeout=15000)
    except PlaywrightTimeoutError:
        pass
    if page.locator("canvas").count() and not page.locator("div[contenteditable='true'][role='textbox']").count():
        input("Inicia sesión escaneando el QR y presiona Enter para continuar.")
    return playwright, context, page


def verificar_whatsapp_numero(page, telefono):
    numero = normalizar_telefono_whatsapp(telefono)
    if not numero:
        return WHATSAPP_ERROR, "Sin teléfono válido"
    page.goto(f"https://web.whatsapp.com/send?phone={numero}", wait_until="domcontentloaded", timeout=60000)
    invalidos = re.compile(r"(phone number shared via url is invalid|número de teléfono.*no es válido|numero de telefono.*no es valido|invalid|no es válido|no existe)", re.I)
    fin = time.time() + 35
    while time.time() < fin:
        if page.locator("footer div[contenteditable='true'][role='textbox']").count() or page.locator("div[contenteditable='true'][data-tab]").count():
            return WHATSAPP_SI, ""
        texto = ""
        try:
            texto = page.locator("body").inner_text(timeout=1000)
        except Exception:
            texto = ""
        if invalidos.search(texto):
            return WHATSAPP_NO, ""
        time.sleep(1)
    return WHATSAPP_ERROR, "No se pudo determinar si el chat existe"


def verificar_whatsapp_por_id(id_prospecto, forzar=False):
    return verificar_whatsapp_lote(ids=[str(id_prospecto)], maximo=1, prioridad=None, forzar=forzar)


def verificar_whatsapp_lote(ids=None, maximo=20, prioridad="Alta", forzar=False):
    df = _asegurar_columnas_whatsapp(asegurar_excel(ARCHIVO_EXCEL))
    maximo = min(int(maximo or 20), 20)
    candidatos = df.copy()
    if ids is not None:
        ids_set = {str(i).strip() for i in ids if str(i).strip()}
        candidatos = candidatos[candidatos["ID"].astype(str).isin(ids_set)]
    elif prioridad:
        candidatos = candidatos[candidatos["Prioridad"].fillna("").astype(str).str.lower() == prioridad.lower()]
    candidatos = candidatos[candidatos["Telefono"].fillna("").astype(str).str.strip().ne("")]
    if not forzar:
        candidatos = candidatos[~candidatos["WhatsApp"].fillna(WHATSAPP_PENDIENTE).astype(str).isin([WHATSAPP_SI, WHATSAPP_NO])]
    candidatos = candidatos.head(maximo)

    resultados = []
    if candidatos.empty:
        return resultados

    playwright, context, page = _sesion_whatsapp()
    try:
        for conteo, (idx, row) in enumerate(candidatos.iterrows(), start=1):
            try:
                estado, error = verificar_whatsapp_numero(page, row.get("Telefono", ""))
            except Exception as exc:
                estado, error = WHATSAPP_ERROR, str(exc)
            df.at[idx, "WhatsApp"] = estado
            df.at[idx, "Fecha_Verificacion_WhatsApp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            df.at[idx, "Error_WhatsApp"] = error
            guardar_excel(df, ARCHIVO_EXCEL)
            resultados.append({"ID": row.get("ID", ""), "Nombre": row.get("Nombre", ""), "Telefono": row.get("Telefono", ""), "WhatsApp": estado, "Error_WhatsApp": error})
            if conteo < len(candidatos):
                time.sleep(random.uniform(4, 9))
            if conteo % 10 == 0 and conteo < len(candidatos):
                time.sleep(random.uniform(30, 60))
    finally:
        context.close()
        playwright.stop()
    return resultados
