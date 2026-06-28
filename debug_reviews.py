import sys
import time
from pathlib import Path
from urllib.parse import quote

from playwright.sync_api import sync_playwright

from buscar_maps import (
    DESKTOP_USER_AGENT,
    DESKTOP_VIEWPORT,
    extraer_rating,
    limpiar,
    preparar_vista_maps_escritorio,
)

OUTPUT_FILE = Path("debug_reviews_output.txt")
MAX_LEN = 160
REVIEW_KEYWORDS = ("rating", "stars", "estrellas", "reviews", "reseñas", "resenas", "opiniones")


def _visible_text(elemento):
    try:
        if hasattr(elemento, "is_visible") and not elemento.is_visible(timeout=200):
            return ""
    except Exception:
        pass
    try:
        return limpiar(elemento.inner_text(timeout=300))
    except Exception:
        try:
            return limpiar(elemento.text_content(timeout=300))
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


def _unique(values):
    seen = set()
    output = []
    for value in values:
        value = limpiar(value)
        if value and value not in seen:
            seen.add(value)
            output.append(value)
    return output


def _section(lines, title, values):
    lines.append(f"\n=== {title} ===")
    for value in _unique(values):
        lines.append(value)


def _short(value):
    value = limpiar(value)
    return value if value and len(value) < MAX_LEN else ""


def diagnosticar_reviews(url):
    lines = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(viewport=DESKTOP_VIEWPORT, user_agent=DESKTOP_USER_AGENT)
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=15000)
        except Exception:
            pass
        preparar_vista_maps_escritorio(page)

        lines.append(f"URL inspeccionada: {page.url}")
        lines.append(f"Viewport usado: {DESKTOP_VIEWPORT}")
        lines.append(f"User agent usado: {DESKTOP_USER_AGENT}")
        h1 = _visible_text(page.locator("h1").first)
        lines.append("\n=== h1 ===")
        lines.append(h1 or "(sin h1 visible)")

        rating = extraer_rating(page)
        lines.append("\n=== rating detectado ===")
        lines.append(rating or "(sin rating detectado)")

        textos = []
        for selector in "span", "button", "a", "div[role='button']", "[role='img']":
            try:
                elementos = page.locator(selector).all()[:700]
            except Exception:
                continue
            for elemento in elementos:
                texto = _short(_visible_text(elemento))
                if texto:
                    textos.append(texto)

        arias = []
        try:
            elementos_aria = page.locator("[aria-label]").all()[:900]
        except Exception:
            elementos_aria = []
        for elemento in elementos_aria:
            aria = _short(_aria_label(elemento))
            if aria:
                arias.append(aria)

        filtros = [
            t for t in textos
            if "(" in t
            or any(k in t.lower() for k in REVIEW_KEYWORDS)
            or (rating and any(r in t for r in {rating, rating.replace(".", ",")}))
        ]
        _section(lines, "textos cortos con rating/paréntesis/reseñas/opiniones/reviews", filtros)
        _section(lines, f'textos visibles menores de {MAX_LEN} caracteres con "(" y ")"', [t for t in textos if "(" in t and ")" in t])
        if rating:
            variantes_rating = {rating, rating.replace(".", ",")}
            _section(lines, f'textos visibles menores de {MAX_LEN} caracteres con rating {rating}', [t for t in textos if any(r in t for r in variantes_rating)])
        else:
            _section(lines, f'textos visibles menores de {MAX_LEN} caracteres con rating', [])
        _section(lines, f'aria-label menores de {MAX_LEN} caracteres con "(" y ")"', [a for a in arias if "(" in a and ")" in a])
        _section(lines, "aria-label con rating/stars/estrellas/reviews/reseñas/opiniones", [a for a in arias if any(k in a.lower() for k in REVIEW_KEYWORDS)])
        context.close()
        browser.close()

    output = "\n".join(lines) + "\n"
    print(output)
    OUTPUT_FILE.write_text(output, encoding="utf-8")


if __name__ == "__main__":
    destino = sys.argv[1].strip() if len(sys.argv) > 1 else input("Pega la URL de Google Maps: ").strip()
    if not destino.startswith("http"):
        destino = f"https://www.google.com/maps/search/{quote(destino)}?hl=es-419"
    diagnosticar_reviews(destino)
