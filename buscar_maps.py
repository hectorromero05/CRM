from playwright.sync_api import sync_playwright
from urllib.parse import quote
import pandas as pd
import time

BUSQUEDAS = [
    "restaurantes Guadalajara",
    "mariscos Guadalajara",
    "taquerías Guadalajara",
    "cafeterías Guadalajara",
    "desayunos Guadalajara",
]

MAX_POR_BUSQUEDA = 40
ARCHIVO = "prospectos_maps.xlsx"
resultados = []

def limpiar(texto):
    return texto.replace("\n", " ").strip() if texto else ""

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(viewport={"width": 1366, "height": 768})

    for busqueda in BUSQUEDAS:
        print(f"\nBuscando: {busqueda}")

        url = f"https://www.google.com/maps/search/{quote(busqueda)}?hl=es-419"
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)

        for _ in range(12):
            page.mouse.wheel(0, 3000)
            time.sleep(1)

        links = []
        anchors = page.locator('a[href*="/maps/place"]').all()

        for a in anchors:
            try:
                href = a.get_attribute("href")
                if href and href not in links:
                    links.append(href)
            except:
                pass

        print(f"Links encontrados: {len(links)}")

        for i, link in enumerate(links[:MAX_POR_BUSQUEDA], start=1):
            page.goto(link, wait_until="domcontentloaded", timeout=60000)
            time.sleep(4)

            def text(selector):
                try:
                    return limpiar(page.locator(selector).first.text_content(timeout=3000))
                except:
                    return ""

            nombre = text("h1")
            telefono = ""
            sitio_web = ""
            rating = ""
            resenas = ""
            direccion = ""

            elementos = page.locator("button, a").all()

            for e in elementos:
                try:
                    t = limpiar(e.inner_text(timeout=800))
                    href = e.get_attribute("href")

                    if not telefono and ("+52" in t or t.startswith("33") or "33 " in t):
                        telefono = t

                    if href and href.startswith("http"):
                        if "google" not in href and "gstatic" not in href and "ggpht" not in href:
                            sitio_web = href

                    if not direccion and ("Guadalajara" in t or "Zapopan" in t or "Tlaquepaque" in t):
                        direccion = t

                    if not rating and ("estrellas" in t.lower() or "stars" in t.lower()):
                        rating = t

                    if not resenas and ("reseñas" in t.lower() or "reviews" in t.lower()):
                        resenas = t
                except:
                    pass

            if nombre:
                resultados.append({
                    "Negocio": nombre,
                    "Nicho": busqueda,
                    "Telefono": telefono,
                    "Tiene_web": "si" if sitio_web else "no",
                    "Sitio_web": sitio_web,
                    "Rating": rating,
                    "Resenas": resenas,
                    "Direccion": direccion,
                    "Google_Maps": link,
                    "Estado": "Pendiente",
                    "Demo": "",
                    "Notas": ""
                })

                print(f"{i}. {nombre} | Web: {'sí' if sitio_web else 'no'} | Tel: {telefono}")

    browser.close()

df = pd.DataFrame(resultados)

if not df.empty:
    df.drop_duplicates(subset=["Negocio"], inplace=True)

df.to_excel(ARCHIVO, index=False)

print(f"\nListo. Archivo creado: {ARCHIVO}")
print(f"Total prospectos: {len(df)}")