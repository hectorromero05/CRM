import shutil
import subprocess
from pathlib import Path


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


def _extraer_url(texto):
    urls = []
    for parte in (texto or "").replace("\r", "\n").split():
        limpia = parte.strip().strip(".,;()[]{}<>")
        if limpia.startswith("https://") and "vercel.app" in limpia:
            urls.append(limpia)
    return urls[-1] if urls else ""


def _nombre_con_sufijo(base, numero):
    return base if numero == 1 else f"{base}-{numero}"


def _es_error_nombre_existente(error):
    texto = str(error or "").lower()
    indicadores = [
        "already exists",
        "project already exists",
        "name is already",
        "taken",
        "conflict",
    ]
    return any(indicador in texto for indicador in indicadores)


def deploy_vercel(carpeta_demo, nombre_proyecto, max_intentos=20):
    """Publica una demo con Vercel CLI y devuelve (url, error, nombre_usado)."""
    carpeta = Path(carpeta_demo).expanduser().resolve()
    if shutil.which("vercel") is None:
        mensaje = "Vercel CLI no está instalado. Instálalo con: npm i -g vercel"
        print(mensaje)
        return "", mensaje, ""

    version = _ejecutar(["vercel", "--version"])
    if version.returncode != 0:
        mensaje = _mensaje_error(version)
        print(mensaje)
        return "", mensaje, ""

    if not carpeta.exists() or not carpeta.is_dir():
        mensaje = f"Carpeta de demo inválida: {carpeta}"
        print(mensaje)
        return "", mensaje, ""

    ultimo_error = ""
    for numero in range(1, max_intentos + 1):
        nombre_usado = _nombre_con_sufijo(nombre_proyecto, numero)
        print(f"Publicando en Vercel: {nombre_usado}")
        deploy = _ejecutar(["vercel", "--prod", "--yes", "--name", nombre_usado], cwd=carpeta)
        salida = "\n".join([deploy.stdout or "", deploy.stderr or ""])
        if deploy.returncode != 0:
            error = _mensaje_error(deploy)
            ultimo_error = error
            if "login" in error.lower() or "not authenticated" in error.lower() or "unauthorized" in error.lower():
                error = "Debes iniciar sesión con: vercel login"
                print(f"No se pudo hacer deploy en Vercel: {error}")
                return "", error, ""
            if _es_error_nombre_existente(error):
                print(f"El proyecto Vercel {nombre_usado} ya existe. Probando otro nombre...")
                continue
            print(f"No se pudo hacer deploy en Vercel: {error}")
            return "", error, ""

        url = _extraer_url(salida)
        if not url:
            error = "No se pudo capturar la URL final del deploy de Vercel."
            print(error)
            return "", error, ""
        print(f"URL Vercel creada: {url}")
        return url, "", nombre_usado

    error = f"No se encontró un nombre disponible para Vercel. Último error: {ultimo_error}"
    print(error)
    return "", error, ""
