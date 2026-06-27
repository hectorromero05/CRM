import time
from datetime import datetime
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from crm_utils import ARCHIVO_EXCEL, NICHOS, ZONAS, asegurar_excel, fusionar_registro, guardar_excel, normalizar_telefono

MAX_POR_BUSQUEDA = 40


def limpiar(texto):
    return texto.replace("\n", " ").strip() if texto else ""



def limpiar_telefono(valor):
    texto = limpiar(valor)
    digitos = normalizar_telefono(texto)
    return texto if len(digitos) >= 8 else ""

def generar_busquedas(nichos=None, zonas=None):
    nichos = nichos or NICHOS
    zonas = zonas or ZONAS
    return [f"{nicho} {zona}" if "guadalajara" in zona.lower() or zona in ["Zapopan", "Tlaquepaque"] else f"{nicho} {zona} Guadalajara" for nicho in nichos for zona in zonas]


def extraer_texto(page, selector, timeout=3000):
    try:
        return limpiar(page.locator(selector).first.text_content(timeout=timeout))
    except Exception:
        return ""


def extraer_detalle(page, link, busqueda):
    page.goto(link, wait_until="domcontentloaded", timeout=60000)
    time.sleep(3)
    nombre = extraer_texto(page, "h1")
    datos = {
        "Nombre": nombre,
        "Nicho": busqueda,
        "Telefono": "",
        "Sitio_web": "",
        "Rating": "",
        "Resenas": "",
        "Direccion": "",
        "Horario": "",
        "Categoria": "",
        "Google_Maps": link,
        "Notas": "",
        "Fecha_busqueda": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    aria = ""
    try:
        aria = " ".join(page.locator("[aria-label]").evaluate_all("els => els.map(e => e.getAttribute('aria-label') || '')"))
    except Exception:
        pass
    try:
        rating = page.locator('[role="img"][aria-label*="estrellas"], [role="img"][aria-label*="stars"]').first.get_attribute("aria-label", timeout=1500)
        datos["Rating"] = limpiar(rating)
    except Exception:
        pass
    try:
        categoria = page.locator('button[jsaction*="category"], button[aria-label*="Categoría"]').first.inner_text(timeout=1500)
        datos["Categoria"] = limpiar(categoria)
    except Exception:
        pass
    for e in page.locator("button, a, div").all()[:350]:
        try:
            t = limpiar(e.inner_text(timeout=500))
            href = e.get_attribute("href") if e.evaluate("el => el.tagName.toLowerCase() === 'a'") else ""
            bajo = t.lower()
            telefono_limpio = limpiar_telefono(t)
            if not datos["Telefono"] and telefono_limpio and ("+52" in t or t.startswith("33") or " 33" in t or len(normalizar_telefono(t)) >= 10):
                datos["Telefono"] = telefono_limpio
            if href and href.startswith("http") and not datos["Sitio_web"] and all(x not in href for x in ["google", "gstatic", "ggpht"]):
                datos["Sitio_web"] = href
            if not datos["Direccion"] and any(z in t for z in ["Guadalajara", "Zapopan", "Tlaquepaque", "Jalisco"]):
                datos["Direccion"] = t
            if not datos["Resenas"] and ("reseña" in bajo or "review" in bajo):
                datos["Resenas"] = t
            if not datos["Horario"] and any(p in bajo for p in ["abre", "cierra", "cerrado", "abierto"]):
                datos["Horario"] = t
        except Exception:
            continue
    if not datos["Rating"] and aria:
        datos["Rating"] = aria[:200]
    return datos if nombre else None


def buscar_prospectos(busquedas=None, max_por_busqueda=MAX_POR_BUSQUEDA, headless=False, archivo=ARCHIVO_EXCEL):
    df = asegurar_excel(archivo)
    agregados = actualizados = 0
    busquedas = busquedas or generar_busquedas()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
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
                for i, link in enumerate(links[:max_por_busqueda], 1):
                    try:
                        registro = extraer_detalle(page, link, busqueda)
                        if not registro:
                            continue
                        df, nuevo = fusionar_registro(df, registro)
                        agregados += int(nuevo); actualizados += int(not nuevo)
                        guardar_excel(df, archivo)
                        print(f"{i}. {registro['Nombre']} | {'nuevo' if nuevo else 'actualizado'}")
                    except Exception as exc:
                        print(f"Error con prospecto {link}: {exc}")
                        guardar_excel(df, archivo)
            except Exception as exc:
                print(f"Error en búsqueda {busqueda}: {exc}")
                guardar_excel(df, archivo)
        browser.close()
    print(f"\nListo: {archivo}. Nuevos: {agregados}. Actualizados/duplicados: {actualizados}. Total: {len(df)}")
    return df


if __name__ == "__main__":
    buscar_prospectos()
