import shutil
import subprocess
from pathlib import Path

from crm_utils import ARCHIVO_EXCEL, asegurar_excel, guardar_excel, normalizar_telefono, slugify
from codex_manager import asegurar_archivos_codex


def _ejecutar(comando, cwd=None, check=True):
    """Ejecuta un comando compatible con Windows y devuelve CompletedProcess."""
    return subprocess.run(
        comando,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
        check=check,
    )


def _mensaje_error(resultado):
    return (resultado.stderr or resultado.stdout or "Error desconocido.").strip()


def _validar_gh():
    if shutil.which("gh") is None:
        print("GitHub CLI no está instalado. Instálalo desde https://cli.github.com/")
        return False
    auth = _ejecutar(["gh", "auth", "status"], check=False)
    if auth.returncode != 0:
        print("Debes iniciar sesión con: gh auth login")
        print(_mensaje_error(auth))
        return False
    return True


def _validar_git():
    if shutil.which("git") is None:
        print("Git no está instalado o no está disponible en PATH.")
        return False
    return True


def _usuario_github():
    resultado = _ejecutar(["gh", "api", "user", "--jq", ".login"], check=False)
    if resultado.returncode != 0:
        print("No se pudo obtener el usuario autenticado de GitHub.")
        print(_mensaje_error(resultado))
        return None
    usuario = resultado.stdout.strip()
    if not usuario:
        print("No se pudo obtener el usuario autenticado de GitHub.")
        return None
    return usuario


def _repo_existe(usuario, nombre_repo):
    resultado = _ejecutar(["gh", "repo", "view", f"{usuario}/{nombre_repo}"], check=False)
    return resultado.returncode == 0


def _preparar_git(carpeta_demo):
    if not (carpeta_demo / ".git").exists():
        init = _ejecutar(["git", "init"], cwd=carpeta_demo, check=False)
        if init.returncode != 0:
            return False, f"Error al ejecutar git init: {_mensaje_error(init)}"

        add = _ejecutar(["git", "add", "."], cwd=carpeta_demo, check=False)
        if add.returncode != 0:
            return False, f"Error al ejecutar git add: {_mensaje_error(add)}"

        commit = _ejecutar(["git", "commit", "-m", "Primera versión"], cwd=carpeta_demo, check=False)
        if commit.returncode != 0:
            return False, f"Error al ejecutar git commit: {_mensaje_error(commit)}"

    rama = _ejecutar(["git", "branch", "-M", "main"], cwd=carpeta_demo, check=False)
    if rama.returncode != 0:
        return False, f"Error al configurar la rama main: {_mensaje_error(rama)}"
    return True, ""



def _commit_cambios_codex(carpeta_demo):
    add = _ejecutar(["git", "add", "prompt_codex.txt", "codex_task.md", "restaurant.json"], cwd=carpeta_demo, check=False)
    if add.returncode != 0:
        return False, f"Error al agregar archivos Codex a git: {_mensaje_error(add)}"

    diff = _ejecutar(["git", "diff", "--cached", "--quiet"], cwd=carpeta_demo, check=False)
    if diff.returncode == 0:
        return True, ""

    commit = _ejecutar(["git", "commit", "-m", "Preparar tarea para Codex Online"], cwd=carpeta_demo, check=False)
    if commit.returncode != 0:
        return False, f"Error al crear commit de archivos Codex: {_mensaje_error(commit)}"
    return True, ""

def _nombre_repo_disponible(usuario, base):
    if not _repo_existe(usuario, base):
        return base
    i = 2
    while True:
        candidato = f"{base}-{i}"
        if not _repo_existe(usuario, candidato):
            return candidato
        i += 1


def crear_repo_demo(id_prospecto, permitir_alternativo=False):
    """Crea un repositorio público en GitHub para la demo de un prospecto."""
    if not _validar_git() or not _validar_gh():
        return None

    df = asegurar_excel(ARCHIVO_EXCEL)
    fila = df[df["ID"].astype(str) == str(id_prospecto).strip()]
    if fila.empty:
        print("ID no encontrado.")
        return None

    prospecto = fila.iloc[0].to_dict()
    nombre = str(prospecto.get("Nombre", "")).strip()
    demo = str(prospecto.get("Demo", "")).strip()
    telefono = str(prospecto.get("Telefono", "")).strip()
    google_maps = str(prospecto.get("Google_Maps", "")).strip()

    if not nombre:
        print("El prospecto no tiene nombre. No se puede crear el repositorio.")
        return None
    if not demo or demo.lower() in {"nan", "none", "null"}:
        print("El prospecto no tiene ruta de demo. Genera una demo primero.")
        return None

    carpeta_demo = Path(demo).expanduser().resolve()
    if not carpeta_demo.exists() or not carpeta_demo.is_dir():
        print(f"Ruta inválida o carpeta de demo inexistente: {carpeta_demo}")
        return None

    nombre_repo = f"{slugify(nombre)}-web"
    usuario = _usuario_github()
    if not usuario:
        return None

    if _repo_existe(usuario, nombre_repo):
        if permitir_alternativo:
            nombre_repo = _nombre_repo_disponible(usuario, nombre_repo)
            print(f"El repositorio base ya existe. Usando nombre alternativo: {nombre_repo}")
        else:
            print(f"El repositorio ya existe: https://github.com/{usuario}/{nombre_repo}")
            print("Operación cancelada.")
            return None

    archivos_codex = asegurar_archivos_codex(carpeta_demo, prospecto)

    ok, error = _preparar_git(carpeta_demo)
    if not ok:
        print(error)
        return None

    ok, error = _commit_cambios_codex(carpeta_demo)
    if not ok:
        print(error)
        return None

    print("Creando repositorio GitHub para:")
    print(f"Nombre: {nombre}")
    print(f"Demo: {carpeta_demo}")
    print(f"Teléfono: {telefono}")
    print(f"Google Maps: {google_maps}")

    crear = _ejecutar(
        ["gh", "repo", "create", nombre_repo, "--public", "--source", ".", "--remote", "origin", "--push"],
        cwd=carpeta_demo,
        check=False,
    )
    if crear.returncode != 0:
        print("No se pudo crear o subir el repositorio.")
        print(_mensaje_error(crear))
        return None

    push = _ejecutar(["git", "push", "-u", "origin", "main"], cwd=carpeta_demo, check=False)
    if push.returncode != 0:
        print("El repositorio fue creado, pero ocurrió un error al hacer push a main.")
        print(_mensaje_error(push))
        return None

    url = f"https://github.com/{usuario}/{nombre_repo}"
    idx = fila.index[0]
    if normalizar_telefono(telefono):
        df.at[idx, "Telefono"] = telefono
    df.at[idx, "Estado"] = "Repositorio creado"
    df.at[idx, "Repositorio_GitHub"] = url
    df.at[idx, "Codex_Task"] = str(archivos_codex["codex_task"])
    df.at[idx, "Restaurant_JSON"] = str(archivos_codex["restaurant_json"])
    df["Telefono"] = df["Telefono"].astype("object")
    guardar_excel(df, ARCHIVO_EXCEL)
    try:
        from generar_demo import sincronizar_datos_demo_excel

        sincronizar_datos_demo_excel(id_prospecto, ARCHIVO_EXCEL)
    except Exception as exc:
        print(f"Aviso: no se pudo sincronizar restaurant.json con Excel: {exc}")

    print("Demo creada:")
    print(carpeta_demo)
    print("\nRepo GitHub:")
    print(url)
    print("\nArchivo para Codex:")
    print(archivos_codex["codex_task"])
    print("\nSiguiente paso:")
    print("Abrir Codex Online, seleccionar el repo y pegar la tarea.")
    return url


def mostrar_prospectos_para_repo():
    df = asegurar_excel(ARCHIVO_EXCEL)
    if df.empty:
        print("No hay prospectos guardados.")
        return
    columnas = ["ID", "Nombre", "Demo"]
    print(df[columnas].to_string(index=False))
    id_prospecto = input("ID del prospecto: ").strip()
    if not id_prospecto:
        print("No se ingresó ID.")
        return
    crear_repo_demo(id_prospecto)
