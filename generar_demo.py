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
    nombre = str(prospecto.get("Nombre", "Restaurante")).strip() or "Restaurante"
    nicho = str(prospecto.get("Nicho", "restaurante")).strip() or "restaurante"
    telefono = str(prospecto.get("Telefono", "")).strip()
    maps = str(prospecto.get("Google_Maps", "")).strip()
    servicios = ["Reservaciones", "Pedidos por WhatsApp", "Ubicación en Google Maps", "Menú destacado"]
    botones = [
        {"texto": "Reservar por WhatsApp", "tipo": "whatsapp", "url": f"https://wa.me/{normalizar_telefono(telefono)}" if normalizar_telefono(telefono) else ""},
        {"texto": "Cómo llegar", "tipo": "maps", "url": maps},
    ]
    return {
        "nombre": nombre,
        "telefono": telefono,
        "whatsapp": telefono,
        "google_maps": maps,
        "direccion": str(prospecto.get("Direccion", "")),
        "horario": str(prospecto.get("Horario", "")),
        "rating": str(prospecto.get("Rating", "")),
        "resenas": str(prospecto.get("Resenas", "")),
        "nicho": nicho,
        "categoria": str(prospecto.get("Categoria", nicho)),
        "sitio_web": str(prospecto.get("Sitio_web", "")),
        "tiene_web": str(prospecto.get("Tiene_web", "")),
        "colores_sugeridos": colores,
        "estilo_sugerido": estilo,
        "palabras_clave_seo": [nombre, nicho, f"{nicho} cerca de mí", "restaurante en Guadalajara", "reservaciones por WhatsApp"],
        "meta_description": f"Conoce {nombre}, {nicho} con ubicación, menú, reseñas y reservaciones por WhatsApp.",
        "servicios": servicios,
        "botones": botones,
        "redes_sociales": {"instagram": "", "facebook": "", "tiktok": ""},
        "imagenes": {"hero": "/hero.jpg", "logo": "/logo.png", "galeria": ["/galeria1.jpg", "/galeria2.jpg", "/galeria3.jpg"]},
        "secciones_sugeridas": ["Hero", "Historia", "Especialidades", "Galería", "Menú", "Mapa", "Reseñas", "CTA final", "Footer"],
    }


def crear_prompt(prospecto):
    datos = crear_restaurant_json(prospecto)
    nombre = datos["nombre"]
    nicho = datos["nicho"]
    colores = _lista_texto(datos["colores_sugeridos"])
    keywords = _lista_texto(datos["palabras_clave_seo"])
    return f"""# Tarea Codex Online — landing premium para {nombre}

## Rol y resultado esperado
Actúa como director creativo, diseñador UI senior y desarrollador frontend React + Vite. Debes transformar este repositorio en una landing profesional para restaurante. No hagas una edición superficial: el sitio final debe parecer un proyecto hecho desde cero y vendible por $15,000–$20,000 MXN.

## Datos del restaurante
- Nombre: {nombre}
- Teléfono: {datos['telefono']}
- WhatsApp: {datos['whatsapp']}
- Google Maps: {datos['google_maps']}
- Dirección: {datos['direccion']}
- Horario: {datos['horario']}
- Rating: {datos['rating']}
- Reseñas: {datos['resenas']}
- Categoría/Nicho: {datos['categoria']} / {nicho}
- Estilo sugerido: {datos['estilo_sugerido']}
- Colores sugeridos: {colores}
- Keywords SEO: {keywords}
- Meta description: {datos['meta_description']}

## Reglas obligatorias de identidad visual
No te limites a cambiar textos. Cambia de forma visible y profunda:
1. Paleta de colores completa.
2. Tipografías y jerarquías.
3. Hero, composición, imagen/fondo y CTA.
4. Iconografía y microdetalles.
5. Estructura de secciones.
6. Botones, estados hover y foco.
7. Fondos, gradientes, patrones o texturas.
8. Tarjetas, bordes, radios y sombras.
9. Animaciones CSS sutiles.
10. Layout responsive, espaciados y ritmo visual.
11. Footer y navegación.

Cada restaurante debe verse distinto. Si el nicho es mariscos usa tema costero con azules, turquesa, arena y blanco. Si es taquería usa rojo, amarillo, negro y estilo mexicano. Si es cafetería usa beige, terracota, café y crema minimalista. Si es parrilla usa verde oscuro, madera, carbón y crema. Si es hamburguesas usa negro, rojo, naranja y estilo urbano. Si es sushi usa negro, rojo, rosa y Japón moderno. Si es pizza usa rojo, crema y verde con sensación italiana.

## Imágenes
Usa siempre rutas locales desde public: /hero.jpg, /logo.png, /galeria1.jpg, /galeria2.jpg, /galeria3.jpg. Nunca dejes imágenes rotas. Implementa fallbacks visuales con gradientes, fondos CSS o placeholders elegantes si una imagen no carga. No dependas de imágenes externas para que la demo funcione.

## Landing obligatoria
Incluye como mínimo: Hero, Historia, Especialidades, Galería, Menú, Mapa, botón WhatsApp, botón Google Maps, Reseñas, CTA final y Footer. El copy debe vender: confianza, sabor, ubicación, facilidad de reservar/pedir y prueba social.

## Componentización obligatoria
Separa App.jsx. Crea componentes en src/components/:
- Hero.jsx
- About.jsx
- Menu.jsx
- Gallery.jsx
- Testimonials.jsx
- Location.jsx
- Footer.jsx
- Navbar.jsx
- WhatsappButton.jsx
Puedes agregar más componentes si mejora la calidad.

## SEO obligatorio
Actualiza index.html y/o el componente SEO según aplique:
- title
- meta description
- keywords
- Open Graph
- Twitter Card
- Schema.org Restaurant en JSON-LD
- Favicon o referencia a logo si existe

## Calidad técnica
Mantén React + Vite. No migres de framework. No agregues dependencias innecesarias. El sitio debe compilar con npm run build. Prioriza mobile-first, accesibilidad básica, semántica HTML, botones con aria-label cuando corresponda, contraste legible y rendimiento.

## Entregable final
Deja el repositorio listo para commit/push/deploy. Ejecuta o recomienda npm run build. Resume archivos modificados y cualquier dato faltante que haya requerido placeholder.
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
