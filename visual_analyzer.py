"""Análisis heurístico de identidad visual para demos de restaurantes.

El objetivo es convertir los datos disponibles del prospecto (Google Maps,
Categoría, Nicho, nombre, fotos, menú y notas) en un perfil visual accionable
para que Codex genere landings distintas y no simples variaciones de plantilla.
"""
from __future__ import annotations

from typing import Any

from crm_utils import normalizar_texto

LAYOUTS_DISPONIBLES = [
    "split hero",
    "full background hero",
    "editorial menu",
    "cards grid",
    "dark neon bar",
    "rustic parrilla",
    "coastal seafood",
    "minimalist cafe",
    "street food energetic",
]

GENERIC_COPY_TO_AVOID = [
    "Una pausa francesa, elegante y cercana",
    "Experiencia cálida y memorable",
    "Restaurante premium",
    "experiencia gastronómica única",
    "sabores inolvidables",
    "calidad y tradición",
]

PHOTO_FIELDS = (
    "Fotos", "Foto", "Imagen", "Imagen_Principal", "Imagen_principal", "Imagenes",
    "Google_Photos", "Google_Images", "Menu", "Menu_URL", "Notas",
)

STYLE_RULES = [
    {
        "keys": ("cafeteria", "cafe", "coffee", "desayuno", "panaderia"),
        "tipo": "Cafetería",
        "concepto": "cafetería con identidad cercana basada en café, pan, desayunos y ritmo de barrio",
        "ambiente": "minimalista, cálido, artesanal, moderno o vintage según fotos reales",
        "colores": ["#6F4E37", "#C89F74", "#F4E8D8", "#2F241D"],
        "tipografia": "serif editorial para titulares + sans limpia para lectura",
        "layout": "minimalist cafe",
        "tono": "cercano, sensorial y cotidiano; mencionar café, desayunos o pan solo si aparece en datos",
        "secciones": ["Hero de barra o producto", "Menú de café/desayunos", "Ambiente", "Galería", "Ubicación", "Reseñas"],
        "keywords": ["café", "artesanal", "desayunos", "barrio", "calidez"],
    },
    {
        "keys": ("bar", "cantina", "pub", "cerveza", "coctel", "night"),
        "tipo": "Bar",
        "concepto": "bar con personalidad nocturna y social basada en luces, música, bebidas y energía urbana",
        "ambiente": "nocturno, neón, oscuro, musical o urbano según fotos",
        "colores": ["#0B0B12", "#7C3AED", "#EC4899", "#22D3EE"],
        "tipografia": "display condensada o geométrica + sans moderna",
        "layout": "dark neon bar",
        "tono": "directo, social, nocturno; evitar prometer lujo si no hay evidencia",
        "secciones": ["Hero nocturno", "Bebidas", "Ambiente/música", "Promos", "Mapa", "Reservas"],
        "keywords": ["noche", "cocteles", "música", "neón", "amigos"],
    },
    {
        "keys": ("marisco", "seafood", "pescado", "camaron", "ceviche", "ostion"),
        "tipo": "Mariscos",
        "concepto": "marisquería fresca y familiar con referencias costeras y platillos del mar",
        "ambiente": "costero, fresco, popular o familiar",
        "colores": ["#0077B6", "#00A6A6", "#F8F1E7", "#D62828"],
        "tipografia": "sans redondeada o editorial fresca + acentos bold",
        "layout": "coastal seafood",
        "tono": "fresco, familiar y apetitoso; hablar de mariscos solo si el nicho/categoría lo indica",
        "secciones": ["Hero costero", "Especialidades del mar", "Menú popular", "Galería", "Cómo llegar", "Reseñas"],
        "keywords": ["fresco", "mar", "familia", "ceviche", "camarón"],
    },
    {
        "keys": ("taqueria", "taco", "tacos", "birria", "tortas", "antojito"),
        "tipo": "Taquería",
        "concepto": "taquería popular y energética con sabor mexicano y ritmo callejero",
        "ambiente": "popular, callejero, mexicano y energético",
        "colores": ["#D62828", "#FBC02D", "#111111", "#F7F1E1"],
        "tipografia": "display mexicana/bold para titulares + sans compacta",
        "layout": "street food energetic",
        "tono": "antojadizo, directo y local; mencionar tacos, salsas o trompo solo si hay datos",
        "secciones": ["Hero callejero", "Tacos favoritos", "Salsas/combos", "Galería", "Ubicación", "WhatsApp"],
        "keywords": ["tacos", "callejero", "salsa", "mexicano", "popular"],
    },
    {
        "keys": ("parrilla", "asador", "carne", "grill", "bbq", "carbon", "steak"),
        "tipo": "Parrilla",
        "concepto": "parrilla rústica con textura de madera, fuego, carbón y cortes al asador",
        "ambiente": "madera, fuego, carbón, verde oscuro y rústico",
        "colores": ["#12372A", "#7A3E1D", "#F2E2C4", "#D97706"],
        "tipografia": "serif robusta o slab + sans fuerte",
        "layout": "rustic parrilla",
        "tono": "contundente, artesanal y de fuego; no inventar cortes específicos",
        "secciones": ["Hero con fuego", "Cortes/especialidades", "Parrilla", "Galería", "Mapa", "Reserva"],
        "keywords": ["fuego", "carbón", "madera", "asador", "cortes"],
    },
    {
        "keys": ("ramen", "sushi", "japones", "japonesa", "yakitori", "roll"),
        "tipo": "Ramen/Sushi",
        "concepto": "cocina japonesa urbana con contraste, ritmo gráfico e inspiración de barra/izakaya",
        "ambiente": "japonés urbano, rojo/negro, amarillo o ilustrado",
        "colores": ["#0F0F0F", "#D90429", "#FFD166", "#F8F5F0"],
        "tipografia": "sans geométrica + display condensada o detalles tipo cartel japonés",
        "layout": "editorial menu",
        "tono": "urbano, preciso y visual; no inventar autenticidad japonesa si no está justificada",
        "secciones": ["Hero de barra/plato", "Ramen o rolls", "Menú editorial", "Galería", "Ubicación", "Pedidos"],
        "keywords": ["japonés", "urbano", "ramen", "sushi", "barra"],
    },
]


def _combined_text(prospecto: dict[str, Any]) -> str:
    parts = [str(prospecto.get(k, "")) for k in ("Nombre", "Nicho", "Categoria", "Direccion", "Horario", "Sitio_web")]
    parts.extend(str(prospecto.get(k, "")) for k in PHOTO_FIELDS)
    return normalizar_texto(" ".join(parts))


def _has_any_word(text: str, words: tuple[str, ...]) -> bool:
    tokens = set(text.split())
    return any(word in tokens or word in text for word in words)


def _photo_hints(text: str) -> dict[str, bool]:
    return {
        "neon": _has_any_word(text, ("neon", "morado", "violeta", "purple", "luces", "antro")),
        "madera": _has_any_word(text, ("madera", "rustico", "rústico", "ladrillo", "carbon", "carbón")),
        "rojo_amarillo": _has_any_word(text, ("rojo", "amarillo", "menu rojo", "menú rojo")),
        "marino": _has_any_word(text, ("mariscos", "playa", "pescado", "camaron", "camarón", "ceviche", "azul", "marino", "costero")),
    }


def analizar_perfil_visual(prospecto: dict[str, Any]) -> dict[str, Any]:
    """Genera un perfil visual estable y explicable para restaurant.json y prompt."""
    text = _combined_text(prospecto)
    rule = next((r for r in STYLE_RULES if any(k in text for k in r["keys"])), None)
    if rule is None:
        rule = {
            "tipo": str(prospecto.get("Categoria") or prospecto.get("Nicho") or "Restaurante"),
            "concepto": "restaurante local con identidad construida desde su nombre, categoría, ubicación y reseñas disponibles",
            "ambiente": "local, honesto y adaptable a las fotos reales del negocio",
            "colores": ["#1F2937", "#B45309", "#F8F1E7", "#111827"],
            "tipografia": "sans moderna con titulares de personalidad moderada",
            "layout": "split hero",
            "tono": "concreto, local y descriptivo; no usar adjetivos premium sin evidencia",
            "secciones": ["Hero", "Especialidades", "Ambiente", "Menú", "Mapa", "Reseñas", "CTA"],
            "keywords": ["local", "cercano", "sabor", "ubicación", "reseñas"],
        }

    hints = _photo_hints(text)
    colores = list(rule["colores"])
    ambiente = rule["ambiente"]
    layout = rule["layout"]
    diferenciadores = [str(prospecto.get("Nombre", "")).strip(), str(prospecto.get("Categoria") or prospecto.get("Nicho") or "").strip()]

    if hints["neon"]:
        colores = ["#09090B", "#7C3AED", "#EC4899", "#22D3EE"]
        ambiente = "nocturno con luces moradas/neón detectadas en referencias"
        layout = "dark neon bar"
        diferenciadores.append("referencias visuales con luces neón/moradas")
    if hints["madera"]:
        colores = ["#2B1A12", "#8B5A2B", "#E7D3B1", "#184E3A"]
        ambiente = "cálido/rústico con madera o texturas naturales detectadas"
        layout = "rustic parrilla" if layout != "dark neon bar" else layout
        diferenciadores.append("madera o estética rústica en referencias")
    if hints["rojo_amarillo"]:
        colores = ["#D62828", "#FBC02D", "#111111", "#FFF4D6"]
        ambiente = "popular y energético con señales rojo/amarillo en menú o marca"
        layout = "street food energetic" if layout not in {"dark neon bar", "rustic parrilla"} else layout
        diferenciadores.append("paleta rojo/amarillo detectada")
    if hints["marino"]:
        colores = ["#006D77", "#00A6A6", "#F8F1E7", "#E76F51"]
        ambiente = "fresco/costero por referencias a comida marina o color azul"
        layout = "coastal seafood" if layout != "dark neon bar" else layout
        diferenciadores.append("referencias marinas o costeras")

    return {
        "tipo_negocio": rule["tipo"],
        "concepto_visual": rule["concepto"],
        "colores": colores,
        "tipografia_sugerida": rule["tipografia"],
        "ambiente": ambiente,
        "estilo_visual": ambiente,
        "layout": layout,
        "layouts_disponibles": LAYOUTS_DISPONIBLES,
        "tono": rule["tono"],
        "secciones_recomendadas": rule["secciones"],
        "palabras_clave_marca": [k for k in rule["keywords"] if k] + [d for d in diferenciadores if d],
        "diferenciadores": [d for d in diferenciadores if d],
        "evitar": GENERIC_COPY_TO_AVOID + [
            "misma estructura visual de la plantilla",
            "mismo hero reutilizado",
            "misma tipografía en todas las demos",
            "misma paleta para todos los restaurantes",
            "textos genéricos no basados en datos reales",
        ],
    }
