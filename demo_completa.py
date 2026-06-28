import shutil
import subprocess
import webbrowser
from pathlib import Path

from codex_manager import _abrir_vscode, _copiar_portapapeles, asegurar_archivos_codex
from crm_utils import ARCHIVO_EXCEL, asegurar_excel, guardar_excel, slugify
from generar_demo import demo_vacia, generar_demo
from vercel_manager import deploy_vercel

GITHUB_OWNER = "hectorromero05"


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


def _ejecutar(comando, cwd=None):
    return subprocess.run(
        comando,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=False,
    )


def _mensaje_error(resultado):
    return (resultado.stderr or resultado.stdout or "Error desconocido.").strip()


def _eliminar_carpetas_heredadas(carpeta_demo, nombre=".git"):
    carpeta = Path(carpeta_demo).expanduser().resolve()
    for heredada in list(carpeta.rglob(nombre)):
        if heredada.is_dir():
            shutil.rmtree(heredada, ignore_errors=True)
            print(f"Carpeta heredada eliminada: {heredada}")


def _nombre_con_sufijo(base, numero):
    return base if numero == 1 else f"{base}-{numero}"


def _git_limpio(carpeta_demo):
    comandos = [
        ["git", "init"],
        ["git", "add", "."],
        ["git", "commit", "-m", "Primera versión"],
        ["git", "branch", "-M", "main"],
    ]
    for comando in comandos:
        resultado = _ejecutar(comando, cwd=carpeta_demo)
        if resultado.returncode != 0:
            return False, f"Error al ejecutar {' '.join(comando)}: {_mensaje_error(resultado)}"
    return True, ""


def _limpiar_remotes(carpeta_demo):
    remotes = _ejecutar(["git", "remote"], cwd=carpeta_demo)
    if remotes.returncode != 0:
        return False, f"Error al leer remotes git: {_mensaje_error(remotes)}"
    for remote in remotes.stdout.splitlines():
        remote = remote.strip()
        if remote:
            borrar = _ejecutar(["git", "remote", "remove", remote], cwd=carpeta_demo)
            if borrar.returncode != 0:
                return False, f"Error al eliminar remote {remote}: {_mensaje_error(borrar)}"
    return True, ""


def _crear_repo_github_limpio(carpeta_demo, base_nombre, max_intentos=20):
    if shutil.which("git") is None:
        return "", "", "Git no está instalado o no está disponible en PATH."
    if shutil.which("gh") is None:
        return "", "", "GitHub CLI no está instalado. Instálalo desde https://cli.github.com/"

    ok, error = _git_limpio(carpeta_demo)
    if not ok:
        return "", "", error

    ultimo_error = ""
    for numero in range(1, max_intentos + 1):
        nombre_proyecto = _nombre_con_sufijo(base_nombre, numero)
        repo_url = f"https://github.com/{GITHUB_OWNER}/{nombre_proyecto}"
        remote_url = f"{repo_url}.git"

        crear = _ejecutar(["gh", "repo", "create", nombre_proyecto, "--public"], cwd=carpeta_demo)
        if crear.returncode != 0:
            ultimo_error = _mensaje_error(crear)
            if "already exists" in ultimo_error.lower() or "name already exists" in ultimo_error.lower():
                print(f"El repositorio {nombre_proyecto} ya existe. Probando otro nombre...")
                continue
            return "", "", f"No se pudo crear el repositorio GitHub: {ultimo_error}"

        ok, error = _limpiar_remotes(carpeta_demo)
        if not ok:
            return "", "", error
        remote = _ejecutar(["git", "remote", "add", "origin", remote_url], cwd=carpeta_demo)
        if remote.returncode != 0:
            return "", "", f"Error al agregar remote origin: {_mensaje_error(remote)}"

        push = _ejecutar(["git", "push", "-u", "origin", "main"], cwd=carpeta_demo)
        if push.returncode != 0:
            return "", "", f"El repositorio fue creado, pero ocurrió un error al hacer push: {_mensaje_error(push)}"

        print(f"repo creado: {repo_url}")
        print(f"remote usado: {remote_url}")
        return repo_url, nombre_proyecto, ""

    return "", "", f"No se encontró un nombre disponible para GitHub. Último error: {ultimo_error}"


def generar_demo_completa(id_prospecto, archivo=ARCHIVO_EXCEL):
    id_limpio = str(id_prospecto).strip()
    df = asegurar_excel(archivo)
    fila = df[df["ID"].astype(str) == id_limpio]
    if fila.empty:
        print("ID no encontrado.")
        return None

    idx = fila.index[0]
    prospecto = fila.iloc[0].to_dict()
    base_nombre_proyecto = f"{slugify(prospecto.get('Nombre'))}-web"
    nombre_proyecto = base_nombre_proyecto
    resumen = {"github": "", "vercel": "", "carpeta": "", "prompt": "", "codex_task": ""}

    try:
        carpeta = generar_demo(id_limpio, archivo=archivo)
        if not carpeta:
            return None
        carpeta = Path(carpeta).expanduser().resolve()
        _eliminar_carpetas_heredadas(carpeta, ".git")
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
        repo_url, nombre_github, error = _crear_repo_github_limpio(carpeta, base_nombre_proyecto)
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        if repo_url:
            resumen["github"] = repo_url
            nombre_proyecto = nombre_github
            df.at[idx, "Repositorio_GitHub"] = repo_url
            df.at[idx, "Estado"] = "Repositorio creado"
        elif error:
            df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error GitHub: {error}")
        guardar_excel(df, archivo)
    except Exception as exc:
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        df.at[idx, "Notas"] = _agregar_nota(df.at[idx, "Notas"], f"Error GitHub: {exc}")
        guardar_excel(df, archivo)
        print(f"No se pudo crear repositorio GitHub: {exc}")

    try:
        _eliminar_carpetas_heredadas(carpeta, ".vercel")
        vercel_url, error, nombre_vercel = deploy_vercel(carpeta, nombre_proyecto)
        df = asegurar_excel(archivo)
        idx = df[df["ID"].astype(str) == id_limpio].index[0]
        if vercel_url:
            resumen["vercel"] = vercel_url
            nombre_proyecto = nombre_vercel or nombre_proyecto
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
