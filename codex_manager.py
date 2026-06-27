import subprocess
import webbrowser
from pathlib import Path

from crm_utils import ARCHIVO_EXCEL, asegurar_excel
from generar_demo import crear_codex_task, crear_restaurant_json, demo_vacia


def asegurar_archivos_codex(carpeta_cliente, prospecto):
    """Crea o actualiza los archivos necesarios para trabajar con Codex Online."""
    carpeta = Path(carpeta_cliente).expanduser().resolve()
    carpeta.mkdir(parents=True, exist_ok=True)

    prompt_path = carpeta / "prompt_codex.txt"
    task_path = carpeta / "codex_task.md"
    restaurant_path = carpeta / "restaurant.json"

    prompt = crear_codex_task(prospecto)
    prompt_path.write_text(prompt, encoding="utf-8")
    task_path.write_text(prompt, encoding="utf-8")

    import json

    restaurant_path.write_text(
        json.dumps(crear_restaurant_json(prospecto), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "prompt_codex": prompt_path,
        "codex_task": task_path,
        "restaurant_json": restaurant_path,
    }


def _abrir_vscode(carpeta):
    try:
        subprocess.Popen(["code", str(carpeta)])
        print(f"Carpeta abierta en VS Code: {carpeta}")
    except FileNotFoundError:
        print("No se encontró el comando 'code'. Abre la carpeta manualmente en VS Code:")
        print(carpeta)


def _copiar_portapapeles(texto, ruta):
    try:
        import pyperclip
    except ImportError:
        print("pyperclip no está instalado. Copia manualmente el contenido de:")
        print(ruta)
        return False
    pyperclip.copy(texto)
    print("Contenido de codex_task.md copiado al portapapeles.")
    return True


def preparar_tarea_codex_online(archivo=ARCHIVO_EXCEL):
    df = asegurar_excel(archivo)
    if df.empty:
        print("No hay prospectos guardados.")
        return None

    repo_creado = df["Repositorio_GitHub"].apply(lambda valor: not demo_vacia(valor))
    mascara = (~df["Demo"].apply(demo_vacia)) | repo_creado
    candidatos = df[mascara]
    if candidatos.empty:
        print("No hay prospectos con demo creada o repositorio creado.")
        return None

    columnas = ["ID", "Nombre", "Nicho", "Demo", "Repositorio_GitHub"]
    print(candidatos[columnas].to_string(index=False))
    id_prospecto = input("ID del prospecto para preparar Codex Online: ").strip()
    fila = df[df["ID"].astype(str) == id_prospecto]
    if fila.empty:
        print("ID no encontrado.")
        return None

    prospecto = fila.iloc[0].to_dict()
    demo = str(prospecto.get("Demo", "")).strip()
    if demo_vacia(demo):
        print("El prospecto no tiene carpeta de demo local registrada.")
        return None

    carpeta = Path(demo).expanduser().resolve()
    if not carpeta.exists() or not carpeta.is_dir():
        print(f"Ruta inválida o carpeta inexistente: {carpeta}")
        return None

    archivos = asegurar_archivos_codex(carpeta, prospecto)
    _abrir_vscode(carpeta)
    contenido = archivos["codex_task"].read_text(encoding="utf-8")
    _copiar_portapapeles(contenido, archivos["codex_task"])
    webbrowser.open("https://chatgpt.com/codex")
    print("Codex Online abierto en el navegador: https://chatgpt.com/codex")
    return archivos["codex_task"]
