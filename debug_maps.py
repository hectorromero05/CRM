import sys
import time
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from buscar_maps import DESKTOP_USER_AGENT, DESKTOP_VIEWPORT, limpiar, preparar_vista_maps_escritorio

URL_DEFAULT = "https://www.google.com/maps/search/restaurante+Guadalajara?hl=es-419"
MAX_TEXTO = 120


def _texto_visible(elemento):
    try:
        if hasattr(elemento, "is_visible") and not elemento.is_visible(timeout=200):
            return ""
    except Exception:
        pass
    try:
        return limpiar(elemento.inner_text(timeout=300))
    except Exception:
        return ""


def _aria_label(elemento):
    try:
        return limpiar(elemento.get_attribute("aria-label", timeout=300) or "")
    except TypeError:
        try:
            return limpiar(elemento.get_attribute("aria-label") or "")
        except Exception:
            return ""
    except Exception:
        return ""


def _imprimir_unicos(titulo, valores):
    print(f"\n=== {titulo} ===")
    vistos = set()
    for valor in valores:
        valor = limpiar(valor)
        if not valor or valor in vistos:
            continue
        vistos.add(valor)
        print(valor)


def inspeccionar_maps(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=DESKTOP_VIEWPORT, user_agent=DESKTOP_USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        time.sleep(3)
        vista_preparada = False
        try:
            enlaces = page.locator('a[href*="/maps/place"]').all()
            if enlaces and "/maps/search/" in page.url:
                enlaces[0].click(timeout=5000)
                preparar_vista_maps_escritorio(page)
                vista_preparada = True
        except Exception:
            pass

        if "/maps/search/" not in page.url and not vista_preparada:
            preparar_vista_maps_escritorio(page)

        print(f"URL inspeccionada: {page.url}")

        textos = []
        for selector in ["span", "button", "div[role='button']", "a"]:
            try:
                elementos = page.locator(selector).all()[:500]
            except Exception:
                continue
            for elemento in elementos:
                texto = _texto_visible(elemento)
                if texto and len(texto) < MAX_TEXTO:
                    textos.append(texto)
        _imprimir_unicos(f"Textos visibles menores de {MAX_TEXTO} caracteres", textos)

        arias = []
        try:
            elementos = page.locator("[aria-label]").all()[:500]
        except Exception:
            elementos = []
        for elemento in elementos:
            aria = _aria_label(elemento)
            if aria:
                arias.append(aria)
        _imprimir_unicos("Aria-label", arias)

        botones = []
        try:
            elementos = page.locator("button").all()[:300]
        except Exception:
            elementos = []
        for elemento in elementos:
            texto = _texto_visible(elemento) or _aria_label(elemento)
            if texto:
                botones.append(texto)
        _imprimir_unicos("Botones", botones)

        spans = []
        try:
            elementos = page.locator("span").all()[:500]
        except Exception:
            elementos = []
        for elemento in elementos:
            texto = _texto_visible(elemento) or _aria_label(elemento)
            if texto:
                spans.append(texto)
        _imprimir_unicos("Spans", spans)
        context.close()
        browser.close()


if __name__ == "__main__":
    destino = sys.argv[1].strip() if len(sys.argv) > 1 else URL_DEFAULT
    if not destino.startswith("http"):
        destino = f"https://www.google.com/maps/search/{quote(destino)}?hl=es-419"
    inspeccionar_maps(destino)
