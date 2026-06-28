import webbrowser
from pathlib import Path

from codex_manager import _abrir_vscode, _copiar_portapapeles, asegurar_archivos_codex
from crm_utils import ARCHIVO_EXCEL, asegurar_excel, guardar_excel, slugify
from generar_demo import demo_vacia, generar_demo
from github_manager import crear_repo_demo
from vercel_manager import deploy_vercel


def _agregar_nota(notas, nueva):
    nueva = str(nueva or "").strip()
    if not nueva:
        return notas
    notas = "" if demo_vacia(notas) else str(notas)
    return f"{notas}\n{nueva}".strip() if notas else nueva


def _guardar_valor(df, idx, columna, valor, archivo=ARCHIVO_EXCEL):
    if columna not in df.columns:
        df[columna] = ""
    if valor is not None and str(valor).strip():
        df.at[idx, columna] = str(valor)
        guardar_excel(df, archivo)


def _abrir_codex():
    try:
        webbrowser.open("https://chatgpt.com/codex")
        print("Codex Online abierto en el navegador: https://chatgpt.com/codex")
    except Exception as exc:
        print(f"No se pudo abrir Codex Online automáticamente: {exc}")


def generar_demo_completa(id_prospecto, archivo=ARCHIVO_EXCEL):
    id_limpio = str(id_prospecto).strip()
    df = asegurar_excel(archivo)
    fila = df[df["ID"].astype(str) == id_limpio]
    if fila.empty:
        print("ID no encontrado.")
        return None

    idx = fila.index[0]
    prospecto = fila.iloc[0].to_dict()
    nombre_proyecto = f"{slugify(prospecto.get('Nombre'))}-web"
    resumen = {"github": "", "vercel": "", "carpeta": "", "prompt": "", "codex_task": ""}

    try:
        carpeta = generar_demo(id_limpio, archivo=archivo)
        if not carpeta:
            return None
        carpeta = Path(carpeta).expanduser().resolve()
        resumen["carpeta"] = str(carpeta)
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        prospecto = df.loc[idx].to_dict()
        guardar_excel(df, archivo)
    except Exception as exc:
        df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error al generar demo local: {exc}")
        guardar_excel(df, archivo)
        print(f"No se pudo generar la demo local: {exc}")
        return None

    try:
        archivos = asegurar_archivos_codex(carpeta, prospecto)
        resumen["prompt"] = str(archivos["prompt_codex"])
        resumen["codex_task"] = str(archivos["codex_task"])
        _guardar_valor(df, idx, "Codex_Task", archivos["codex_task"], archivo)
        _guardar_valor(df, idx, "Restaurant_JSON", archivos["restaurant_json"], archivo)
    except Exception as exc:
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error al crear archivos Codex: {exc}")
        guardar_excel(df, archivo)
        print(f"No se pudieron crear archivos Codex: {exc}")

    try:
        repo_url = crear_repo_demo(id_limpio, permitir_alternativo=True)
        if repo_url:
            resumen["github"] = repo_url
    except Exception as exc:
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error GitHub: {exc}")
        guardar_excel(df, archivo)
        print(f"No se pudo crear repositorio GitHub: {exc}")

    try:
        vercel_url, error = deploy_vercel(carpeta, nombre_proyecto)
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        if vercel_url:
            resumen["vercel"] = vercel_url
            df.at[idx, "Vercel_URL"] = vercel_url
            df.at[idx, "Vercel_Project_Name"] = nombre_proyecto
            df.at[idx, "Estado"] = "Demo publicada"
        elif error:
            df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error Vercel: {error}")
        guardar_excel(df, archivo)
    except Exception as exc:
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error Vercel: {exc}")
        guardar_excel(df, archivo)
        print(f"No se pudo hacer deploy en Vercel: {exc}")

    task_path = Path(resumen["codex_task"] or carpeta / "codex_task.md")
    if task_path.exists():
        try:
            contenido = task_path.read_text(encoding="utf-8")
            _copiar_portapapeles(contenido, task_path)
        except Exception as exc:
            print(f"No se pudo copiar codex_task.md al portapapeles: {exc}")
    _abrir_codex()
    _abrir_vscode(carpeta)

    df = asegurar_excel(archivo)
    idx = df[df["ID"].astype(str) == id_limpio].index[0]
    if resumen["github"]:
        df.at[idx, "Repositorio_GitHub"] = resumen["github"]
    if resumen["vercel"]:
        df.at[idx, "Vercel_URL"] = resumen["vercel"]
        df.at[idx, "Vercel_Project_Name"] = nombre_proyecto
        df.at[idx, "Estado"] = "Demo publicada"
    guardar_excel(df, archivo)

    print("""
===================================

Demo creada:
{carpeta}

Repositorio GitHub:
{github}

Deploy Vercel:
{vercel}

Prompt:
{prompt}

Codex Task:
{codex_task}

El contenido ya fue copiado al portapapeles.

Ahora solo selecciona el repositorio en Codex y presiona Ctrl+V.

===================================
""".format(**resumen))
    return resumen


def mostrar_prospectos_para_demo_completa():
    df = asegurar_excel(ARCHIVO_EXCEL)
    if df.empty:
        print("No hay prospectos guardados.")
        return None
    columnas = ["ID", "Nombre", "Nicho", "Telefono", "Prioridad", "Estado", "Demo"]
    print("Prospectos disponibles:")
    print(df[columnas].to_string(index=False))
    id_prospecto = input("ID del prospecto: ").strip()
    if not id_prospecto:
        print("No se ingresó ID.")
        return None
    return generar_demo_completa(id_prospecto)
