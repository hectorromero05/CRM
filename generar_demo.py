import re
import shutil
from pathlib import Path

from crm_utils import (
    ARCHIVO_EXCEL, CLIENTES_DEFAULT, PLANTILLA_DEFAULT, asegurar_excel, carpeta_unica,
    estilo_por_nicho, guardar_excel, reemplazar_en_archivo, slugify,
)

PLACEHOLDERS = {
    "NOMBRE_RESTAURANTE": "Nombre",
    "RESTAURANTE_NOMBRE": "Nombre",
    "TELEFONO_RESTAURANTE": "Telefono",
    "WHATSAPP_RESTAURANTE": "Telefono",
    "GOOGLE_MAPS_RESTAURANTE": "Google_Maps",
    "DIRECCION_RESTAURANTE": "Direccion",
    "NICHO_RESTAURANTE": "Nicho",
}


def elegir_prospecto(id_prospecto=None, archivo=ARCHIVO_EXCEL):
    df = asegurar_excel(archivo)
    if df.empty:
        print("No hay prospectos guardados.")
        return None, df
    if id_prospecto is None:
        print(df[["ID", "Nombre", "Nicho", "Telefono", "Prioridad", "Estado"]].to_string(index=False))
        id_prospecto = input("ID del prospecto para generar demo: ").strip()
    fila = df[df["ID"].astype(str) == str(id_prospecto)]
    if fila.empty:
        print("ID no encontrado.")
        return None, df
    return fila.iloc[0].to_dict(), df


def crear_prompt(prospecto):
    estilo, colores = estilo_por_nicho(prospecto.get("Nicho", ""))
    nombre = prospecto.get("Nombre", "Restaurante")
    nicho = prospecto.get("Nicho", "restaurante")
    seo = f"Página web para {nombre}, {nicho}, con menú, ubicación, galería, reseñas y botón de WhatsApp."
    return f"""# Prompt para adaptar demo web de restaurante

Actúa como desarrollador frontend experto en React + Vite. Adapta esta plantilla para vender una página web profesional a este negocio.

## Datos del negocio
- Nombre: {nombre}
- Teléfono / WhatsApp: {prospecto.get('Telefono', '')}
- Google Maps: {prospecto.get('Google_Maps', '')}
- Dirección: {prospecto.get('Direccion', '')}
- Nicho: {nicho}
- Rating / reseñas: {prospecto.get('Rating', '')} / {prospecto.get('Resenas', '')}

## Estilo visual sugerido
- Estilo: {estilo}
- Colores: {colores}
- Sensación: moderno, apetitoso, local, confiable y optimizado para convertir visitas en mensajes de WhatsApp.

## Secciones recomendadas
1. Hero con nombre del restaurante, propuesta de valor y botones a WhatsApp / Google Maps.
2. Menú destacado con 6 platillos de ejemplo coherentes con el nicho.
3. Galería con imágenes desde public/hero.jpg, public/galeria1.jpg, public/galeria2.jpg y public/galeria3.jpg.
4. Sección de historia o ambiente del restaurante.
5. Reseñas y confianza usando rating/reseñas si están disponibles.
6. Ubicación con dirección, botón de Google Maps y horario.
7. CTA final para reservar o pedir información por WhatsApp.

## Archivos a adaptar
- index.html: cambia <title> y meta description con el texto SEO.
- src/App.jsx o App.jsx: reemplaza textos genéricos por el nombre, teléfono, dirección, nicho y links reales.
- src/App.css o App.css: aplica la paleta de colores sugerida, buen responsive y estilo visual de restaurante.

## Imágenes sugeridas
Usa estas rutas aunque todavía sean placeholders:
- public/hero.jpg
- public/logo.png
- public/galeria1.jpg
- public/galeria2.jpg
- public/galeria3.jpg

## Texto SEO
{seo}

No inventes datos sensibles. Si falta información, usa copy comercial genérico y deja comentarios claros para completar después.
"""


def generar_demo(id_prospecto=None, plantilla=PLANTILLA_DEFAULT, clientes=CLIENTES_DEFAULT, archivo=ARCHIVO_EXCEL):
    prospecto, df = elegir_prospecto(id_prospecto, archivo)
    if not prospecto:
        return None
    plantilla_path = Path(plantilla)
    clientes_path = Path(clientes)
    if not plantilla_path.exists():
        print(f"No existe la plantilla: {plantilla_path}")
        return None
    clientes_path.mkdir(parents=True, exist_ok=True)
    nombre_carpeta = f"{slugify(prospecto.get('Nombre'))}-web"
    destino = carpeta_unica(clientes_path, nombre_carpeta)
    shutil.copytree(plantilla_path, destino)

    reemplazos = {clave: str(prospecto.get(columna, "")) for clave, columna in PLACEHOLDERS.items()}
    reemplazos.update({
        "Mariscos El Jarocho": str(prospecto.get("Nombre", "")),
        "La Patrona": str(prospecto.get("Nombre", "")),
        "Quilombo": str(prospecto.get("Nombre", "")),
        "Restaurante": str(prospecto.get("Nombre", "Restaurante")),
    })
    for relativo in ["index.html", "src/App.jsx", "App.jsx", "src/App.css", "App.css"]:
        reemplazar_en_archivo(destino / relativo, reemplazos)

    descripcion = f"Demo web para {prospecto.get('Nombre')} - {prospecto.get('Nicho', 'restaurante')} en Guadalajara."
    index = destino / "index.html"
    if index.exists():
        texto = index.read_text(encoding="utf-8")
        if "<title>" in texto:
            texto = re.sub(r"<title>.*?</title>", f"<title>{prospecto.get('Nombre')} | Sitio web demo</title>", texto, flags=re.S)
        if "meta name=\"description\"" in texto:
            texto = re.sub(r'<meta name="description" content=".*?"\s*/?>', f'<meta name="description" content="{descripcion}" />', texto, flags=re.S)
        index.write_text(texto, encoding="utf-8")

    (destino / "prompt_codex.txt").write_text(crear_prompt(prospecto), encoding="utf-8")
    for img in ["hero.jpg", "logo.png", "galeria1.jpg", "galeria2.jpg", "galeria3.jpg"]:
        placeholder = destino / "public" / img
        placeholder.parent.mkdir(exist_ok=True)
        if not placeholder.exists():
            placeholder.write_text("Placeholder: reemplazar por imagen del restaurante.\n", encoding="utf-8")

    idx = df[df["ID"].astype(str) == str(prospecto["ID"])].index[0]
    df.at[idx, "Demo"] = str(destino)
    guardar_excel(df, archivo)
    print(f"Demo creada en: {destino}")
    print(f"Prompt creado en: {destino / 'prompt_codex.txt'}")
    return destino


if __name__ == "__main__":
    generar_demo()
