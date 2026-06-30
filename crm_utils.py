import os
import re
import unicodedata
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path

import pandas as pd

ARCHIVO_EXCEL = "prospectos_restaurantes.xlsx"

COLUMNAS = [
    "ID", "Nombre", "Nicho", "Telefono", "Tiene_web", "Sitio_web", "Rating", "Resenas",
    "Direccion", "Horario", "Categoria", "Google_Maps", "Posible_duplicado", "Prioridad",
    "Puntaje_Prioridad", "Motivo_Prioridad",
    "Estado", "Demo", "Repositorio_GitHub", "Vercel_URL", "Vercel_Project_Name",
    "Codex_Task", "Restaurant_JSON", "Ruta_Local", "URL_GitHub", "URL_Vercel",
    "Proyecto_Creado", "Repo_Creado", "Codex_Completado", "Deploy_Completado",
    "Fecha_Proyecto", "Fecha_Deploy", "Tiempo_Generacion",
    "Ultimo_Contacto", "Proximo_Seguimiento", "Persona_Contacto", "Canal",
    "Probabilidad_Cierre", "Valor_Estimado", "Historial_Comercial",
    "WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp",
    "Notas", "Fecha_busqueda",
]

ESTADOS = [
    "Pendiente", "Contactado", "Respondió", "Interesado", "Demo creada", "Demo enviada",
    "Cotización enviada", "Demo publicada", "Cerrado", "Perdido",
]

NICHOS = [
    "restaurantes", "mariscos", "taquerías", "cafeterías", "desayunos",
    "hamburguesas", "sushi", "ramen", "pizza",
]

ZONAS = [
    "Guadalajara", "Zapopan", "Tlaquepaque", "Providencia", "Chapalita", "Americana",
    "Santa Tere", "Jardines Universidad", "Centro Guadalajara", "Ciudad del Sol",
]

PLANTILLA_DEFAULT = r"C:\Users\carrera\.vscode\codigos\Pagina Web\Plantillas\Restaurante-web"
CLIENTES_DEFAULT = r"C:\Users\carrera\.vscode\codigos\Pagina Web\Clientes"


def normalizar_texto(valor):
    if pd.isna(valor) or valor is None:
        return ""
    texto = unicodedata.normalize("NFKD", str(valor).strip().lower())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9+ ]+", " ", texto)).strip()


def normalizar_telefono(valor):
    return re.sub(r"\D+", "", "" if pd.isna(valor) else str(valor))


def slugify(valor):
    texto = normalizar_texto(valor)
    texto = re.sub(r"[^a-z0-9]+", "-", texto).strip("-")
    return texto or "restaurante"


def parse_float(valor):
    if pd.isna(valor):
        return 0.0
    match = re.search(r"\d+(?:[\.,]\d+)?", str(valor))
    return float(match.group(0).replace(",", ".")) if match else 0.0


def parse_int(valor):
    if pd.isna(valor):
        return 0
    texto = str(valor).lower().replace(",", "").replace(".", "")
    match = re.search(r"\d+", texto)
    return int(match.group(0)) if match else 0


def asegurar_excel(ruta=ARCHIVO_EXCEL):
    if not os.path.exists(ruta):
        pd.DataFrame(columns=COLUMNAS).to_excel(ruta, index=False)
    texto_columnas = [
        "Demo", "Repositorio_GitHub", "Vercel_URL", "Vercel_Project_Name",
        "Codex_Task", "Restaurant_JSON", "Ruta_Local", "URL_GitHub", "URL_Vercel",
        "Proyecto_Creado", "Repo_Creado", "Codex_Completado", "Deploy_Completado",
        "Fecha_Proyecto", "Fecha_Deploy", "Tiempo_Generacion", "Estado", "Notas", "Telefono",
        "Motivo_Prioridad", "Ultimo_Contacto", "Proximo_Seguimiento", "Persona_Contacto",
        "Canal", "Probabilidad_Cierre", "Valor_Estimado", "Historial_Comercial",
        "WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp",
    ]
    df = pd.read_excel(ruta, dtype={col: object for col in texto_columnas})
    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = ""
    for columna in texto_columnas:
        if columna in df.columns:
            df[columna] = df[columna].fillna("").astype("object")
    return df[COLUMNAS]


def guardar_excel(df, ruta=ARCHIVO_EXCEL):
    df = df.copy()
    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = ""
    df["Resenas"] = pd.to_numeric(df["Resenas"], errors="coerce").fillna(0).astype(int)
    for columna in [
        "Demo", "Repositorio_GitHub", "Vercel_URL", "Vercel_Project_Name",
        "Codex_Task", "Restaurant_JSON", "Ruta_Local", "URL_GitHub", "URL_Vercel",
        "Proyecto_Creado", "Repo_Creado", "Codex_Completado", "Deploy_Completado",
        "Fecha_Proyecto", "Fecha_Deploy", "Tiempo_Generacion", "Estado", "Notas", "Telefono",
        "Motivo_Prioridad", "Ultimo_Contacto", "Proximo_Seguimiento", "Persona_Contacto",
        "Canal", "Probabilidad_Cierre", "Valor_Estimado", "Historial_Comercial",
        "WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp",
    ]:
        if columna in df.columns:
            df[columna] = df[columna].fillna("").astype("object")
    for idx in df.index:
        df.at[idx, "Tiene_web"] = tiene_web(df.at[idx, "Sitio_web"])
        prioridad = calcular_prioridad(df.loc[idx].to_dict())
        df.at[idx, "Prioridad"] = prioridad["Prioridad"]
        df.at[idx, "Puntaje_Prioridad"] = prioridad["Puntaje_Prioridad"]
        df.at[idx, "Motivo_Prioridad"] = prioridad["Motivo_Prioridad"]
    df = marcar_posibles_duplicados(df)
    df = df[COLUMNAS]
    df.to_excel(ruta, index=False)


def siguiente_id(df):
    if df.empty or "ID" not in df:
        return 1
    ids = pd.to_numeric(df["ID"], errors="coerce").dropna()
    return int(ids.max()) + 1 if not ids.empty else 1


DOMINIOS_WEB_IGNORADOS = (
    "google.com", "maps.google", "gstatic.com", "ggpht.com", "googleusercontent.com",
    "business.google", "support.google", "schema.org", "wa.me", "whatsapp",
    "facebook.com", "instagram.com", "tiktok.com", "ubereats", "rappi", "didi-food",
    "menu", "linktr.ee", "beacons.ai",
)

NICHOS_OBJETIVO_PRIORIDAD = (
    "restaurante", "mariscos", "taqueria", "cafeteria", "desayunos", "sushi",
    "ramen", "pizza", "hamburguesas", "bar", "parrilla",
)

FRANQUICIAS_GRANDES = (
    "mcdonald", "burger king", "kfc", "starbucks", "domino", "subway", "pizza hut",
    "little caesars", "carls jr", "toks", "vips", "ihop", "chilis", "applebee",
)


def sitio_web_real(sitio):
    sitio = str(sitio or "").strip()
    if not sitio:
        return False
    parsed = urlparse(sitio if re.match(r"^https?://", sitio, re.I) else f"https://{sitio}")
    dominio = (parsed.netloc or parsed.path.split("/", 1)[0]).lower().replace("www.", "")
    if not dominio or "." not in dominio:
        return False
    return not any(ignorado in dominio or ignorado in sitio.lower() for ignorado in DOMINIOS_WEB_IGNORADOS)


def tiene_web(sitio):
    return "sí" if sitio_web_real(sitio) else "no"


def _coincide(texto, opciones):
    texto = normalizar_texto(texto)
    return any(opcion in texto for opcion in opciones)


def calcular_prioridad(prospecto):
    web_real = sitio_web_real(prospecto.get("Sitio_web")) or normalizar_texto(prospecto.get("Tiene_web")) in {"si", "sí"}
    telefono = bool(normalizar_telefono(prospecto.get("Telefono")))
    rating = parse_float(prospecto.get("Rating"))
    resenas = parse_int(prospecto.get("Resenas"))
    categoria_nicho = f"{prospecto.get('Categoria', '')} {prospecto.get('Nicho', '')}"
    direccion = bool(str(prospecto.get("Direccion") or "").strip())
    horario = bool(str(prospecto.get("Horario") or "").strip())
    fotos = any(str(prospecto.get(c) or "").strip() for c in ("Fotos", "Foto", "Imagen", "Imagen_Principal", "Imagen_principal"))
    franquicia = _coincide(f"{prospecto.get('Nombre', '')} {categoria_nicho}", FRANQUICIAS_GRANDES)

    puntos, razones = 0, []
    def add(valor, razon):
        nonlocal puntos
        puntos += valor; razones.append(razon)

    add(-3 if web_real else 3, "ya tiene sitio web real" if web_real else "sin web real")
    add(3 if telefono else -2, "tiene teléfono" if telefono else "sin teléfono")
    if rating >= 4.5: add(2, f"rating {rating:g}")
    elif rating >= 4.0: add(1, f"rating {rating:g}")
    elif rating < 4.0 and rating != 0: add(-2, f"rating bajo {rating:g}")
    if resenas >= 200: add(2, f"{resenas} reseñas")
    elif resenas >= 80: add(1, f"{resenas} reseñas")
    elif resenas == 0 and rating >= 4.5 and telefono: add(1, "reseñas no disponibles con buen rating y teléfono")
    elif resenas < 30 and resenas != 0: add(-1, f"pocas reseñas ({resenas})")
    if _coincide(categoria_nicho, NICHOS_OBJETIVO_PRIORIDAD): add(2, "nicho objetivo")
    if direccion: add(1, "dirección completa")
    if horario: add(1, "horario visible")
    if fotos: add(1, "tiene fotos")
    if franquicia: add(-2, "parece franquicia grande")

    if puntos >= 8: prioridad = "Alta"
    elif puntos >= 5: prioridad = "Media"
    else: prioridad = "Baja"

    if web_real and prioridad != "Baja":
        prioridad = "Media" if prospecto.get("Sitio_web_Malo") or prospecto.get("Web_no_carga") else "Baja"
    if not web_real and telefono and rating >= 4.5 and prioridad != "Alta" and puntos >= 7:
        prioridad = "Alta"
    if not web_real and telefono and rating >= 4.0 and prioridad == "Baja":
        prioridad = "Media"
    if not telefono and prioridad == "Alta":
        prioridad = "Media"
    if not web_real and not telefono and prioridad == "Alta":
        prioridad = "Media"

    motivo = f"{prioridad}: " + ", ".join(razones[:5])
    return {"Prioridad": prioridad, "Puntaje_Prioridad": puntos, "Motivo_Prioridad": motivo}


def clasificar_prioridad(registro):
    return calcular_prioridad(registro)["Prioridad"]


def preparar_registro(datos, nuevo_id):
    registro = {col: datos.get(col, "") for col in COLUMNAS}
    registro["ID"] = datos.get("ID") or nuevo_id
    registro["Tiene_web"] = tiene_web(registro.get("Sitio_web"))
    registro["Posible_duplicado"] = registro.get("Posible_duplicado") or "no"
    prioridad = calcular_prioridad(registro)
    registro["Prioridad"] = prioridad["Prioridad"]
    registro["Puntaje_Prioridad"] = prioridad["Puntaje_Prioridad"]
    registro["Motivo_Prioridad"] = prioridad["Motivo_Prioridad"]
    registro["Estado"] = registro.get("Estado") or "Pendiente"
    registro["Fecha_busqueda"] = registro.get("Fecha_busqueda") or datetime.now().strftime("%Y-%m-%d %H:%M")
    return registro


def encontrar_duplicado(df, registro):
    nombre = normalizar_texto(registro.get("Nombre"))
    telefono = normalizar_telefono(registro.get("Telefono"))
    maps = normalizar_texto(registro.get("Google_Maps"))
    direccion = normalizar_texto(registro.get("Direccion"))
    for idx, fila in df.iterrows():
        fila_maps = normalizar_texto(fila.get("Google_Maps"))
        fila_telefono = normalizar_telefono(fila.get("Telefono"))
        fila_nombre = normalizar_texto(fila.get("Nombre"))
        fila_direccion = normalizar_texto(fila.get("Direccion"))
        if maps and maps == fila_maps:
            return idx
        if telefono and telefono == fila_telefono:
            return idx
        if nombre and direccion and nombre == fila_nombre and direccion == fila_direccion:
            return idx
    return None


def marcar_posibles_duplicados(df):
    vistos = {}
    posibles = set()
    for idx, fila in df.iterrows():
        claves = []
        maps = normalizar_texto(fila.get("Google_Maps"))
        telefono = normalizar_telefono(fila.get("Telefono"))
        nombre = normalizar_texto(fila.get("Nombre"))
        direccion = normalizar_texto(fila.get("Direccion"))
        if maps:
            claves.append(("maps", maps))
        if telefono:
            claves.append(("telefono", telefono))
        if nombre and direccion:
            claves.append(("nombre_direccion", nombre, direccion))
        for clave in claves:
            if clave in vistos:
                posibles.update({idx, vistos[clave]})
            else:
                vistos[clave] = idx
    df["Posible_duplicado"] = ["sí" if idx in posibles else "no" for idx in df.index]
    return df


def fusionar_registro(df, registro):
    idx = encontrar_duplicado(df, registro)
    if idx is None:
        registro = preparar_registro(registro, siguiente_id(df))
        return marcar_posibles_duplicados(pd.concat([df, pd.DataFrame([registro])], ignore_index=True)), True
    for columna, valor in registro.items():
        if columna in df.columns and str(valor or "").strip() and not str(df.at[idx, columna] or "").strip():
            df.at[idx, columna] = valor
    df.at[idx, "Tiene_web"] = tiene_web(df.at[idx, "Sitio_web"])
    prioridad = calcular_prioridad(df.loc[idx].to_dict())
    df.at[idx, "Prioridad"] = prioridad["Prioridad"]
    df.at[idx, "Puntaje_Prioridad"] = prioridad["Puntaje_Prioridad"]
    df.at[idx, "Motivo_Prioridad"] = prioridad["Motivo_Prioridad"]
    if "Posible_duplicado" in df.columns:
        df.at[idx, "Posible_duplicado"] = "no"
    return marcar_posibles_duplicados(df), False


def estilo_por_nicho(nicho):
    n = normalizar_texto(nicho)
    if "marisco" in n:
        return "estilo costero premium", ["azul océano", "turquesa", "blanco", "arena"]
    if "taquer" in n:
        return "estilo mexicano popular", ["rojo", "amarillo", "negro", "blanco"]
    if "cafeter" in n or "desayuno" in n:
        return "estilo cálido", ["beige", "café", "crema", "terracota"]
    if "argent" in n or "parrilla" in n:
        return "estilo parrilla/argentino", ["verde oscuro", "madera", "crema", "negro carbón"]
    if "ramen" in n or "sushi" in n or "japones" in n:
        return "estilo japonés urbano", ["amarillo", "negro", "rojo", "rosa"]
    if "hamburg" in n:
        return "estilo urbano", ["negro", "rojo", "naranja"]
    if "pizza" in n or "italiano" in n:
        return "trattoria italiana familiar", ["rojo tomate", "crema", "verde albahaca", "madera clara"]
    return "moderno, limpio, adaptable a celular", ["negro", "blanco", "gris", "color acento adaptable"]


def carpeta_unica(base, nombre):
    destino = Path(base) / nombre
    if not destino.exists():
        return destino
    i = 2
    while True:
        candidato = Path(base) / f"{nombre}-{i}"
        if not candidato.exists():
            return candidato
        i += 1


def reemplazar_en_archivo(path, reemplazos):
    archivo = Path(path)
    if not archivo.exists() or not archivo.is_file():
        return False
    try:
        texto = archivo.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return False
    original = texto
    for viejo, nuevo in reemplazos.items():
        texto = texto.replace(viejo, nuevo)
    if texto != original:
        archivo.write_text(texto, encoding="utf-8")
    return texto != original
