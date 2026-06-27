import json
import re
import shutil
from pathlib import Path

from crm_utils import (
    ARCHIVO_EXCEL, CLIENTES_DEFAULT, PLANTILLA_DEFAULT, asegurar_excel, carpeta_unica,
    estilo_por_nicho, guardar_excel, normalizar_telefono, reemplazar_en_archivo, slugify,
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


def demo_vacia(valor):
    if valor is None:
        return True
    texto = str(valor).strip()
    return not texto or texto.lower() in {"nan", "none", "null"}


def _valor_no_vacio(valor):
    return not demo_vacia(valor)


def _leer_restaurant_json(path):
    ruta = Path(str(path or "")).expanduser()
    if not ruta.exists() or not ruta.is_file():
        return {}
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def sincronizar_datos_demo_excel(id_prospecto, archivo=ARCHIVO_EXCEL):
    """Sincroniza campos de la demo con Excel sin borrar teléfonos existentes."""
    df = asegurar_excel(archivo)
    fila = df[df["ID"].astype(str) == str(id_prospecto).strip()]
    if fila.empty:
        print("ID no encontrado.")
        return df

    idx = fila.index[0]
    restaurant_json = str(df.at[idx, "Restaurant_JSON"] or "").strip()
    datos_json = _leer_restaurant_json(restaurant_json)

    telefono_excel = str(df.at[idx, "Telefono"] or "").strip()
    telefono_json = str(datos_json.get("telefono") or datos_json.get("whatsapp") or "").strip()
    if normalizar_telefono(telefono_json) and not normalizar_telefono(telefono_excel):
        df.at[idx, "Telefono"] = telefono_json

    campos_json = {
        "Google_Maps": "google_maps",
        "Demo": "demo",
        "Repositorio_GitHub": "repositorio_github",
        "Codex_Task": "codex_task",
        "Restaurant_JSON": "restaurant_json",
    }
    for columna, clave_json in campos_json.items():
        valor_actual = df.at[idx, columna] if columna in df.columns else ""
        valor_json = str(datos_json.get(clave_json, "")).strip()
        if valor_json and not _valor_no_vacio(valor_actual):
            df.at[idx, columna] = valor_json

    df["Telefono"] = df["Telefono"].astype("object")
    guardar_excel(df, archivo)
    return df


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


def _lista_texto(valores):
    if isinstance(valores, (list, tuple)):
        return ", ".join(str(v) for v in valores)
    return str(valores or "")


def crear_restaurant_json(prospecto):
    estilo, colores = estilo_por_nicho(prospecto.get("Nicho", ""))
    secciones = [
        "Hero con propuesta de valor y CTA a WhatsApp",
        "Menú o productos destacados",
        "Galería de ambiente y platillos",
        "Historia breve del restaurante",
        "Reseñas y confianza",
        "Ubicación, horarios y Google Maps",
        "CTA final para reservar o pedir por WhatsApp",
    ]
    imagenes = ["/hero.jpg", "/logo.png", "/galeria1.jpg", "/galeria2.jpg", "/galeria3.jpg"]
    return {
        "nombre": str(prospecto.get("Nombre", "")),
        "telefono": str(prospecto.get("Telefono", "")),
        "whatsapp": str(prospecto.get("Telefono", "")),
        "google_maps": str(prospecto.get("Google_Maps", "")),
        "direccion": str(prospecto.get("Direccion", "")),
        "nicho": str(prospecto.get("Nicho", "")),
        "categoria": str(prospecto.get("Categoria", "")),
        "rating": str(prospecto.get("Rating", "")),
        "resenas": str(prospecto.get("Resenas", "")),
        "sitio_web": str(prospecto.get("Sitio_web", "")),
        "tiene_web": str(prospecto.get("Tiene_web", "")),
        "estilo_sugerido": estilo,
        "colores_sugeridos": colores,
        "secciones_recomendadas": secciones,
        "imagenes_recomendadas": imagenes,
    }


def crear_prompt(prospecto):
    datos = crear_restaurant_json(prospecto)
    nombre = datos["nombre"] or "Restaurante"
    nicho = datos["nicho"] or "restaurante"
    colores = _lista_texto(datos["colores_sugeridos"])
    secciones = "\n".join(f"- {s}" for s in datos["secciones_recomendadas"])
    imagenes = "\n".join(f"- {img}" for img in datos["imagenes_recomendadas"])
    title = f"{nombre} | {nicho}"
    description = f"Landing page profesional para {nombre}: {nicho}, ubicación, galería, reseñas y botón de WhatsApp."
    return f"""Adapta esta plantilla para crear una landing page profesional para {nombre}.

Actúa como desarrollador frontend senior especializado en React + Vite y páginas de restaurantes listas para vender. Trabaja sobre este repositorio manteniendo la estructura existente.

## Datos del restaurante
- Nombre del restaurante: {nombre}
- Teléfono: {datos['telefono']}
- WhatsApp: {datos['whatsapp']}
- Google Maps: {datos['google_maps']}
- Dirección: {datos['direccion']}
- Nicho: {nicho}
- Categoría: {datos['categoria']}
- Rating: {datos['rating']}
- Reseñas: {datos['resenas']}
- Sitio web actual: {datos['sitio_web']}
- Tiene web: {datos['tiene_web']}

## Estilo visual sugerido
- Estilo: {datos['estilo_sugerido']}
- Paleta de colores sugerida: {colores}
- Debe sentirse moderno, apetitoso, confiable, rápido y optimizado para celular.

## Secciones recomendadas
{secciones}

## Rutas de imágenes locales disponibles
Usa estas rutas desde la carpeta public del proyecto:
{imagenes}

## Archivos que debes modificar
1. src/App.jsx
   - Reemplaza textos genéricos por contenido comercial para {nombre}.
   - Agrega CTAs claros para WhatsApp y Google Maps.
   - Crea secciones coherentes con el nicho {nicho}.
   - Agrega un botón flotante de WhatsApp visible en móvil y escritorio.
2. src/App.css
   - Aplica la paleta sugerida: {colores}.
   - Optimiza todo para celular primero, con diseño responsive.
   - Mejora espaciados, tipografía, tarjetas, botones y galería.
3. index.html
   - Actualiza el title a: {title}
   - Actualiza la meta description a: {description}

## Reglas técnicas obligatorias
- Mantén React + Vite; no migres a otro framework.
- No uses Tailwind CSS.
- No agregues dependencias innecesarias.
- Mantén las imágenes con rutas locales /hero.jpg, /logo.png, /galeria1.jpg, /galeria2.jpg y /galeria3.jpg cuando existan.
- No dejes imágenes rotas: en src/App.jsx agrega fallback visual para hero, logo, galería y tarjetas de platillos usando onError, estados de carga o contenedores alternativos; en src/App.css usa gradientes de fondo cuando falten imágenes locales.
- Si las imágenes locales no existen, usa placeholders visuales con gradientes CSS o imágenes temporales de Unsplash pertinentes al restaurante.
- Optimiza para celular, rendimiento y claridad comercial.
- No inventes datos sensibles. Si falta un dato, usa copy genérico y deja el código fácil de editar.

## Objetivo final
Deja una landing page profesional, visualmente atractiva y lista para mostrar al restaurante, con enfoque en que el visitante haga clic en WhatsApp o abra Google Maps.
"""


def crear_codex_task(prospecto):
    return crear_prompt(prospecto)

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

    prompt_path = destino / "prompt_codex.txt"
    task_path = destino / "codex_task.md"
    restaurant_path = destino / "restaurant.json"
    prompt_path.write_text(crear_prompt(prospecto), encoding="utf-8")
    task_path.write_text(crear_codex_task(prospecto), encoding="utf-8")
    restaurant_path.write_text(
        json.dumps(crear_restaurant_json(prospecto), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    public_path = destino / "public"
    public_path.mkdir(exist_ok=True)
    (public_path / "README_IMAGENES.txt").write_text(
        "Reemplaza estas imágenes por archivos reales del restaurante antes de publicar:\n"
        "- hero.jpg: imagen principal del local o platillo estrella.\n"
        "- logo.png: logo del restaurante con fondo transparente si es posible.\n"
        "- galeria1.jpg: foto del ambiente o fachada.\n"
        "- galeria2.jpg: foto de platillo destacado.\n"
        "- galeria3.jpg: foto de clientes, mesa servida o producto destacado.\n"
        "\nSi alguna imagen falta, la demo debe mostrar gradientes CSS o imágenes temporales de Unsplash para evitar imágenes rotas.\n",
        encoding="utf-8",
    )

    idx = df[df["ID"].astype(str) == str(prospecto["ID"])].index[0]
    telefono = str(prospecto.get("Telefono", "")).strip()
    if normalizar_telefono(telefono):
        df.at[idx, "Telefono"] = telefono
    df.at[idx, "Demo"] = str(destino)
    df.at[idx, "Estado"] = "Demo creada"
    df.at[idx, "Codex_Task"] = str(task_path)
    df.at[idx, "Restaurant_JSON"] = str(restaurant_path)
    df["Telefono"] = df["Telefono"].astype("object")
    guardar_excel(df, archivo)
    sincronizar_datos_demo_excel(prospecto["ID"], archivo)
    print("Demo creada:")
    print(destino)
    print("\nArchivo para Codex:")
    print(task_path)
    print("\nSiguiente paso:")
    print("Abrir Codex Online, seleccionar el repo y pegar la tarea.")
    return destino


def prospectos_para_demo_lote(df):
    demo = df["Demo"].apply(demo_vacia)
    prioridad = df["Prioridad"].astype(str).str.strip().str.lower() == "alta"
    estados = df["Estado"].astype(str).str.strip().str.lower().isin({"pendiente", "contactado"})
    return df[prioridad & estados & demo]


def generar_demos_lote(ids, plantilla=PLANTILLA_DEFAULT, clientes=CLIENTES_DEFAULT, archivo=ARCHIVO_EXCEL):
    creadas = []
    fallidas = []
    for id_prospecto in ids:
        id_limpio = str(id_prospecto).strip()
        if not id_limpio:
            continue
        try:
            destino = generar_demo(id_limpio, plantilla=plantilla, clientes=clientes, archivo=archivo)
            if destino:
                creadas.append({
                    "id": id_limpio,
                    "carpeta": Path(destino),
                    "prompt": Path(destino) / "prompt_codex.txt",
                    "codex_task": Path(destino) / "codex_task.md",
                })
            else:
                fallidas.append({"id": id_limpio, "error": "No se pudo crear la demo."})
        except Exception as exc:
            fallidas.append({"id": id_limpio, "error": str(exc)})
            print(f"Error al crear demo para ID {id_limpio}: {exc}")
    return {"creadas": creadas, "fallidas": fallidas}


if __name__ == "__main__":
    generar_demo()
