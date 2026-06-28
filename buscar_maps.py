import re
import time
from datetime import datetime
from urllib.parse import quote, urlparse

from playwright.sync_api import sync_playwright

from crm_utils import ARCHIVO_EXCEL, NICHOS, ZONAS, asegurar_excel, clasificar_prioridad, fusionar_registro, guardar_excel, tiene_web

MAX_POR_BUSQUEDA = 40
GOOGLE_DOMINIOS_IGNORADOS = (
    "google.com",
    "gstatic.com",
    "ggpht.com",
    "maps.google.com",
    "support.google.com",
    "business.google.com",
)
TELEFONO_REGEX = re.compile(r"(?:\+52\s*)?(?:\(?\d{2,3}\)?[\s\-]*)?\d{3,4}[\s\-]*\d{4}")


def limpiar(texto):
    if texto is None:
        return ""
    texto = str(texto).replace("\ue0b0", " ").replace("\n", " ").replace("\r", " ").replace("\t", " ")
    texto = re.sub(r"[^\w\s+().,/:;@#&%\-áéíóúÁÉÍÓÚñÑ]", " ", texto, flags=re.UNICODE)
    return re.sub(r"\s+", " ", texto).strip()


def limpiar_telefono(valor):
    texto = limpiar(valor)
    if not texto or len(texto) > 40:
        return ""
    match = TELEFONO_REGEX.search(texto)
    if not match:
        return ""
    telefono = limpiar(match.group(0))
    digitos = re.sub(r"\D+", "", telefono)
    if digitos.startswith("52") and len(digitos) == 12:
        pass
    elif len(digitos) != 10:
        return ""
    return re.sub(r"\s+", " ", telefono.replace("-", " ")).strip()


def generar_busquedas(nichos=None, zonas=None):
    nichos = nichos or NICHOS
    zonas = zonas or ZONAS
    return [f"{nicho} {zona}" if "guadalajara" in zona.lower() or zona in ["Zapopan", "Tlaquepaque"] else f"{nicho} {zona} Guadalajara" for nicho in nichos for zona in zonas]


def texto_locator(locator, timeout=1500):
    try:
        return limpiar(locator.first.inner_text(timeout=timeout))
    except Exception:
        try:
            return limpiar(locator.first.text_content(timeout=timeout))
        except Exception:
            return ""


def atributo_locator(locator, atributo, timeout=1500):
    try:
        return limpiar(locator.first.get_attribute(atributo, timeout=timeout))
    except Exception:
        return ""


def extraer_nombre(page):
    return texto_locator(page.locator("h1"))


def extraer_telefono(page):
    try:
        for link in page.locator('a[href^="tel:"]').all()[:10]:
            telefono = limpiar_telefono((link.get_attribute("href") or "").replace("tel:", ""))
            if telefono:
                return telefono
    except Exception:
        pass
    for selector in ['[aria-label*="Teléfono"]', '[aria-label*="Telefono"]', '[aria-label*="Phone"]']:
        try:
            for elemento in page.locator(selector).all()[:20]:
                telefono = limpiar_telefono(elemento.get_attribute("aria-label") or elemento.inner_text(timeout=500))
                if telefono:
                    return telefono
        except Exception:
            continue
    try:
        for boton in page.locator("button").all()[:120]:
            telefono = limpiar_telefono(boton.inner_text(timeout=500))
            if telefono:
                return telefono
    except Exception:
        pass
    try:
        for elemento in page.locator("button, a, div[role='button'], span").all()[:250]:
            texto = limpiar(elemento.inner_text(timeout=300))
            if texto and len(texto) <= 40:
                telefono = limpiar_telefono(texto)
                if telefono:
                    return telefono
    except Exception:
        pass
    return ""


def extraer_rating(page):
    candidatos = [
        '[role="img"][aria-label*="estrellas"]',
        '[role="img"][aria-label*="stars"]',
        'span[aria-label*="estrellas"]',
        'span[aria-label*="stars"]',
    ]
    for selector in candidatos:
        texto = atributo_locator(page.locator(selector), "aria-label") or texto_locator(page.locator(selector))
        match = re.search(r"\d+(?:[\.,]\d+)?", texto)
        if match:
            return match.group(0).replace(",", ".")
    return ""


def extraer_resenas(page):
    for selector in ['button[aria-label*="reseñas"]', 'button[aria-label*="opiniones"]', 'button[aria-label*="reviews"]', 'span[aria-label*="reviews"]']:
        texto = atributo_locator(page.locator(selector), "aria-label") or texto_locator(page.locator(selector))
        if texto:
            match = re.search(r"[\(\s]([\d,.]+)[\)\s]", f" {texto} ")
            if match:
                return re.sub(r"\D+", "", match.group(1))
    return ""


def extraer_direccion(page):
    for selector in ['[aria-label*="Dirección"]', '[aria-label*="Address"]', 'button[data-item-id="address"]']:
        texto = atributo_locator(page.locator(selector), "aria-label") or texto_locator(page.locator(selector))
        texto = re.sub(r"^(Dirección|Address)[:\s]*", "", texto, flags=re.I).strip()
        if texto and len(texto) <= 180:
            return texto
    return ""


def extraer_sitio_web(page):
    try:
        for enlace in page.locator('a[href^="http"]').all()[:200]:
            href = enlace.get_attribute("href") or ""
            dominio = urlparse(href).netloc.lower().replace("www.", "")
            if dominio and not any(ignorado in dominio for ignorado in GOOGLE_DOMINIOS_IGNORADOS):
                return href.split("?")[0]
    except Exception:
        pass
    return ""


def extraer_horario(page):
    for selector in ['[aria-label*="Horario"]', '[aria-label*="Hours"]', 'div[role="button"]']:
        texto = atributo_locator(page.locator(selector), "aria-label") or texto_locator(page.locator(selector))
        if texto and len(texto) <= 180 and re.search(r"abierto|cerrado|abre|cierra|horario|hours", texto, re.I):
            return texto
    return ""


def extraer_categoria(page):
    for selector in ['button[jsaction*="category"]', 'button[aria-label*="Categoría"]', 'button[aria-label*="Category"]']:
        texto = texto_locator(page.locator(selector)) or atributo_locator(page.locator(selector), "aria-label")
        if texto and len(texto) <= 80:
            return texto
    return ""


def extraer_detalle(page, link, busqueda):
    page.goto(link, wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)
    nombre = extraer_nombre(page)
    if not nombre:
        return None
    telefono = extraer_telefono(page)
    print(f"Telefono encontrado: {telefono}")
    return {
        "Nombre": nombre,
        "Nicho": busqueda,
        "Telefono": telefono,
        "Sitio_web": extraer_sitio_web(page),
        "Rating": extraer_rating(page),
        "Resenas": extraer_resenas(page),
        "Direccion": extraer_direccion(page),
        "Horario": extraer_horario(page),
        "Categoria": extraer_categoria(page),
        "Google_Maps": link,
        "Notas": "",
        "Fecha_busqueda": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def buscar_prospectos(busquedas=None, max_por_busqueda=MAX_POR_BUSQUEDA, headless=False, archivo=ARCHIVO_EXCEL):
    df = asegurar_excel(archivo)
    agregados = actualizados = procesados_sin_guardar = 0
    busquedas = busquedas or generar_busquedas()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        try:
            for busqueda in busquedas:
                try:
                    print(f"\nBuscando: {busqueda}")
                    page.goto(f"https://www.google.com/maps/search/{quote(busqueda)}?hl=es-419", wait_until="domcontentloaded", timeout=60000)
                    time.sleep(7)
                    for _ in range(10):
                        page.mouse.wheel(0, 3000)
                        time.sleep(0.8)
                    links = []
                    for a in page.locator('a[href*="/maps/place"]').all():
                        try:
                            href = a.get_attribute("href")
                            if href and href not in links:
                                links.append(href)
                        except Exception:
                            pass
                    print(f"Links encontrados: {len(links)}")
                    for link in links[:max_por_busqueda]:
                        try:
                            registro = extraer_detalle(page, link, busqueda)
                            if not registro:
                                continue
                            df, nuevo = fusionar_registro(df, registro)
                            registro["Tiene_web"] = tiene_web(registro.get("Sitio_web"))
                            prioridad = clasificar_prioridad(registro)
                            print(f"{registro['Nombre']} | {registro['Telefono']} | Web: {registro['Tiene_web']} | {registro['Rating']} | {registro['Resenas']} | {prioridad}")
                            agregados += int(nuevo); actualizados += int(not nuevo); procesados_sin_guardar += 1
                            if procesados_sin_guardar >= 10:
                                guardar_excel(df, archivo); procesados_sin_guardar = 0
                        except Exception as exc:
                            print(f"Error con prospecto {link}: {exc}")
                            guardar_excel(df, archivo); procesados_sin_guardar = 0
                except Exception as exc:
                    print(f"Error en búsqueda {busqueda}: {exc}")
                    guardar_excel(df, archivo); procesados_sin_guardar = 0
        except KeyboardInterrupt:
            print("\nInterrumpido por usuario. Guardando prospectos antes de salir...")
            guardar_excel(df, archivo)
            raise
        finally:
            guardar_excel(df, archivo)
            browser.close()
    print(f"\nListo: {archivo}. Nuevos: {agregados}. Actualizados/duplicados: {actualizados}. Total: {len(df)}")
    return df


if __name__ == "__main__":
    buscar_prospectos()
