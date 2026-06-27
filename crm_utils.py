import os
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

ARCHIVO_EXCEL = "prospectos_restaurantes.xlsx"

COLUMNAS = [
    "ID", "Nombre", "Nicho", "Telefono", "Tiene_web", "Sitio_web", "Rating", "Resenas",
    "Direccion", "Horario", "Categoria", "Google_Maps", "Prioridad", "Estado", "Demo",
    "Notas", "Fecha_busqueda", "Repositorio_GitHub",
]

ESTADOS = [
    "Pendiente", "Contactado", "Respondió", "Interesado", "Demo creada", "Demo enviada",
    "Cotización enviada", "Cerrado", "Perdido",
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
    df = pd.read_excel(ruta, dtype={"Demo": object})
    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = ""
    df["Demo"] = df["Demo"].fillna("").astype(object)
    return df[COLUMNAS]


def guardar_excel(df, ruta=ARCHIVO_EXCEL):
    df = df.copy()
    for columna in COLUMNAS:
        if columna not in df.columns:
            df[columna] = ""
    df["Demo"] = df["Demo"].fillna("").astype(object)
    df = df[COLUMNAS]
    df.to_excel(ruta, index=False)


def siguiente_id(df):
    if df.empty or "ID" not in df:
        return 1
    ids = pd.to_numeric(df["ID"], errors="coerce").dropna()
    return int(ids.max()) + 1 if not ids.empty else 1


def tiene_web(sitio):
    return "sí" if str(sitio or "").strip() else "no"


def clasificar_prioridad(registro):
    web = normalizar_texto(registro.get("Tiene_web") or tiene_web(registro.get("Sitio_web")))
    telefono = bool(normalizar_telefono(registro.get("Telefono")))
    rating = parse_float(registro.get("Rating"))
    resenas = parse_int(registro.get("Resenas"))
    if web in {"si", "sí"} or not telefono:
        return "Baja"
    if rating >= 4.3 and resenas > 80:
        return "Alta"
    return "Media"


def preparar_registro(datos, nuevo_id):
    registro = {col: datos.get(col, "") for col in COLUMNAS}
    registro["ID"] = datos.get("ID") or nuevo_id
    registro["Tiene_web"] = tiene_web(registro.get("Sitio_web"))
    registro["Prioridad"] = clasificar_prioridad(registro)
    registro["Estado"] = registro.get("Estado") or "Pendiente"
    registro["Fecha_busqueda"] = registro.get("Fecha_busqueda") or datetime.now().strftime("%Y-%m-%d %H:%M")
    return registro


def encontrar_duplicado(df, registro):
    nombre = normalizar_texto(registro.get("Nombre"))
    telefono = normalizar_telefono(registro.get("Telefono"))
    maps = normalizar_texto(registro.get("Google_Maps"))
    direccion = normalizar_texto(registro.get("Direccion"))
    for idx, fila in df.iterrows():
        if nombre and nombre == normalizar_texto(fila.get("Nombre")):
            return idx
        if telefono and telefono == normalizar_telefono(fila.get("Telefono")):
            return idx
        if maps and maps == normalizar_texto(fila.get("Google_Maps")):
            return idx
        if direccion and direccion == normalizar_texto(fila.get("Direccion")):
            return idx
    return None


def fusionar_registro(df, registro):
    idx = encontrar_duplicado(df, registro)
    if idx is None:
        registro = preparar_registro(registro, siguiente_id(df))
        return pd.concat([df, pd.DataFrame([registro])], ignore_index=True), True
    for columna, valor in registro.items():
        if columna in df.columns and str(valor or "").strip() and not str(df.at[idx, columna] or "").strip():
            df.at[idx, columna] = valor
    df.at[idx, "Tiene_web"] = tiene_web(df.at[idx, "Sitio_web"])
    df.at[idx, "Prioridad"] = clasificar_prioridad(df.loc[idx].to_dict())
    return df, False


def estilo_por_nicho(nicho):
    n = normalizar_texto(nicho)
    if "marisco" in n:
        return "costero moderno", "azul, blanco y turquesa"
    if "taquer" in n:
        return "mexicano popular", "rojo, amarillo y negro"
    if "cafeter" in n or "desayuno" in n:
        return "cálido y artesanal", "beige, café y crema"
    if "argent" in n or "parrilla" in n:
        return "parrilla elegante", "verde oscuro, madera y crema"
    if "ramen" in n or "sushi" in n:
        return "japonés urbano", "amarillo, negro y rojo"
    if "hamburg" in n:
        return "urbano casual", "negro, rojo y naranja"
    if "pizza" in n:
        return "italiano familiar", "rojo, crema y verde"
    return "restaurante moderno", "negro, crema y dorado"


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
