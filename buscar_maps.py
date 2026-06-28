import re
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

import pandas as pd

from playwright.sync_api import sync_playwright

from crm_utils import (
    ARCHIVO_EXCEL,
    NICHOS,
    ZONAS,
    asegurar_excel,
    clasificar_prioridad,
    encontrar_duplicado,
    fusionar_registro,
    guardar_excel,
    normalizar_texto,
    preparar_registro,
    siguiente_id,
    tiene_web,
)

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
RESENAS_PARENTESIS_REGEX = re.compile(r"\(([\d\.,]+)\)")
RESENAS_TEXTO_REGEX = re.compile(r"([\d\.,]+)\s*(?:reviews?|reseñas|resenas|opiniones)", re.I)


def normalizar_nombre(valor):
    return normalizar_texto(valor)


def _valor_vacio(valor):
    return not str(valor or "").strip()


def _actualizar_datos_faltantes(df, idx, registro):
    for columna, valor in registro.items():
        if columna in df.columns and str(valor or "").strip() and _valor_vacio(df.at[idx, columna]):
            df.at[idx, columna] = valor
    df.at[idx, "Tiene_web"] = tiene_web(df.at[idx, "Sitio_web"])
    df.at[idx, "Prioridad"] = clasificar_prioridad(df.loc[idx].to_dict())
    return df


def extraer_registro_desde_pagina(page, google_maps_url, nicho="Google Maps URL"):
    nombre = extraer_nombre(page)
    if not nombre:
        raise ValueError("No se pudo extraer el nombre del negocio desde Google Maps.")
    registro = {
        "Nombre": nombre,
        "Nicho": nicho,
        "Telefono": extraer_telefono(page),
        "Sitio_web": extraer_sitio_web(page),
        "Rating": extraer_rating(page),
        "Resenas": extraer_resenas(page),
        "Direccion": extraer_direccion(page),
        "Horario": extraer_horario(page),
        "Categoria": extraer_categoria(page),
        "Google_Maps": google_maps_url,
        "Notas": "",
        "Fecha_busqueda": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }
    registro["Tiene_web"] = tiene_web(registro.get("Sitio_web"))
    registro["Prioridad"] = clasificar_prioridad(registro)
    return registro


def agregar_prospecto_desde_maps_url(url, archivo=ARCHIVO_EXCEL, headless=False, actualizar_faltantes=None):
    url = str(url or "").strip()
    if not url:
        raise ValueError("Debes ingresar un link de Google Maps.")

    archivo = Path(archivo)
    df = asegurar_excel(archivo)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page(viewport={"width": 1366, "height": 768})
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            try:
                page.wait_for_load_state("networkidle", timeout=15000)
            except Exception:
                pass
            time.sleep(3)
            final_url = page.url or url
            if "google" not in final_url and "goo.gl" not in final_url and "maps.app" not in final_url:
                raise ValueError(f"El link redirigió fuera de Google Maps: {final_url}")
            registro = extraer_registro_desde_pagina(page, final_url)
        except Exception as exc:
            raise RuntimeError(f"No se pudo abrir o leer el link de Google Maps: {exc}") from exc
        finally:
            browser.close()

    idx = encontrar_duplicado(df, registro)
    if idx is not None:
        existente_id = df.at[idx, "ID"]
        print("Este prospecto ya existe")
        print(f"ID: {existente_id}")
        if actualizar_faltantes is None:
            respuesta = input("¿Deseas actualizar los datos faltantes? (s/N): ").strip().lower()
            actualizar_faltantes = respuesta in {"s", "si", "sí", "y", "yes"}
        if actualizar_faltantes:
            df = _actualizar_datos_faltantes(df, idx, registro)
            guardar_excel(df, archivo)
        return {"nuevo": False, "actualizado": bool(actualizar_faltantes), "id": existente_id, "registro": df.loc[idx].to_dict(), "archivo": str(archivo)}

    registro = preparar_registro(registro, siguiente_id(df))
    df = pd.concat([df, pd.DataFrame([registro])], ignore_index=True)
    guardar_excel(df, archivo)
    return {"nuevo": True, "actualizado": False, "id": registro["ID"], "registro": registro, "archivo": str(archivo)}


def imprimir_resumen_prospecto(registro):
    print("\nResumen del prospecto")
    print(f"Nombre: {registro.get('Nombre', '')}")
    print(f"Teléfono: {registro.get('Telefono', '')}")
    print(f"Web: {registro.get('Tiene_web') or tiene_web(registro.get('Sitio_web'))}")
    print(f"Rating: {registro.get('Rating', '')}")
    print(f"Reseñas: {registro.get('Resenas', '')}")
    print(f"Prioridad: {registro.get('Prioridad') or clasificar_prioridad(registro)}")
    print(f"Dirección: {registro.get('Direccion', '')}")


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


RATING_SELECTORES = [
    '[role="img"][aria-label*="estrellas"]',
    '[role="img"][aria-label*="stars"]',
    'span[aria-label*="estrellas"]',
    'span[aria-label*="stars"]',
]


def _iter_nodos_rating(page):
    for selector in RATING_SELECTORES:
        try:
            elementos = page.locator(selector).all()[:20]
        except Exception:
            continue
        for elemento in elementos:
            try:
                if hasattr(elemento, "is_visible") and not elemento.is_visible(timeout=300):
                    continue
            except Exception:
                pass
            yield elemento


def _texto_nodo_rating(elemento):
    textos = []
    try:
        textos.append(elemento.get_attribute("aria-label", timeout=300) or "")
    except TypeError:
        try:
            textos.append(elemento.get_attribute("aria-label") or "")
        except Exception:
            pass
    except Exception:
        pass
    try:
        textos.append(elemento.inner_text(timeout=300))
    except Exception:
        pass
    for texto in textos:
        texto = limpiar(texto)
        if texto:
            return texto
    return ""


def _texto_contenedor_rating(elemento, rating=""):
    try:
        textos = elemento.evaluate(
            r"""
            (node, rating) => {
                const limpiar = (value) => (value || '').replace(/\s+/g, ' ').trim();
                const textos = [];
                let actual = node;
                for (let i = 0; actual && i < 5; i += 1, actual = actual.parentElement) {
                    const texto = limpiar(actual.innerText || actual.textContent || '');
                    if (texto && texto.length <= 120) textos.push(texto);
                    const aria = limpiar(actual.getAttribute && actual.getAttribute('aria-label'));
                    if (aria && aria.length <= 120) textos.push(aria);
                }
                return [...new Set(textos)];
            }
            """,
            rating,
        )
    except Exception:
        textos = []
    textos = [limpiar(texto) for texto in textos if _texto_corto_resenas(texto)]
    if rating:
        con_rating = [texto for texto in textos if rating in texto or rating.replace('.', ',') in texto]
        con_parentesis = [texto for texto in con_rating if RESENAS_PARENTESIS_REGEX.search(texto)]
        if con_parentesis:
            return con_parentesis[0]
        if con_rating:
            return con_rating[0]
    return textos[0] if textos else _texto_nodo_rating(elemento)


def _obtener_rating_y_texto(page):
    for elemento in _iter_nodos_rating(page):
        texto_rating = _texto_nodo_rating(elemento)
        match = re.search(r"\d+(?:[\.,]\d+)?", texto_rating)
        if match:
            rating = match.group(0).replace(",", ".")
            return rating, _texto_contenedor_rating(elemento, rating)
    return "", ""


def extraer_rating(page):
    rating, _ = _obtener_rating_y_texto(page)
    return rating


def limpiar_numero_resenas(texto):
    texto = limpiar(texto)
    if not texto:
        return 0
    texto = texto.strip().strip("()")
    texto = texto.replace(",", "").replace(".", "")
    if not texto.isdigit():
        return 0
    try:
        return int(texto)
    except Exception:
        return 0


def _texto_corto_resenas(texto, limite=160):
    texto = limpiar(texto)
    if not texto or len(texto) >= limite:
        return ""
    return texto


def _extraer_resenas_desde_texto(texto):
    texto = _texto_corto_resenas(texto)
    if not texto:
        return 0
    for regex in (RESENAS_TEXTO_REGEX, RESENAS_PARENTESIS_REGEX):
        match = regex.search(texto)
        if match:
            return limpiar_numero_resenas(match.group(1))
    return 0


def _iter_textos_resenas_visibles(page):
    try:
        valores = page.locator(
            "span:visible, button:visible, a:visible, div[role='button']:visible, "
            "[role='img']:visible, [aria-label]:visible"
        ).evaluate_all(
            r"""
            (nodes) => {
                const limpiar = (value) => (value || '').replace(/\s+/g, ' ').trim();
                const valores = [];
                for (const node of nodes) {
                    const texto = limpiar(node.innerText || node.textContent || '');
                    const aria = limpiar(node.getAttribute && node.getAttribute('aria-label'));
                    for (const valor of [texto, aria]) {
                        if (valor && valor.length < 160) valores.push(valor);
                    }
                }
                return [...new Set(valores)];
            }
            """
        )
    except Exception:
        return
    palabras_resenas = re.compile(r"reviews?|reseñas|resenas|opiniones", re.I)
    for texto in valores:
        texto = _texto_corto_resenas(texto)
        if texto and (RESENAS_PARENTESIS_REGEX.search(texto) or palabras_resenas.search(texto)):
            yield texto


def extraer_resenas(page):
    """Extrae reseñas desde textos/aria-labels cortos visibles detectables con debug_reviews.py."""
    rating, texto_rating = _obtener_rating_y_texto(page)
    candidatos = [texto_rating, *_iter_textos_resenas_visibles(page)]
    for texto in candidatos:
        texto = _texto_corto_resenas(texto)
        if not texto:
            continue
        print(f"Texto reseñas encontrado:\n{texto}")
        resenas = _extraer_resenas_desde_texto(texto)
        if resenas:
            print(f"Reseñas:\n{resenas}")
            return resenas

    print("Reseñas:\n0")
    return 0


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
                            print(f"{registro['Nombre']} | {registro['Telefono']} | Web: {registro['Tiene_web']} | Rating: {registro['Rating']} | Reseñas: {registro['Resenas']} | {prioridad}")
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
