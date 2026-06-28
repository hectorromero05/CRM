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


def deploy_vercel(carpeta_demo, nombre_proyecto):
    """Publica una demo con Vercel CLI y devuelve (url, error)."""
    carpeta = Path(carpeta_demo).expanduser().resolve()
    if shutil.which("vercel") is None:
        mensaje = "Vercel CLI no está instalado. Instálalo con: npm i -g vercel"
        print(mensaje)
        return "", mensaje

    version = _ejecutar(["vercel", "--version"])
    if version.returncode != 0:
        mensaje = _mensaje_error(version)
        print(mensaje)
        return "", mensaje

    if not carpeta.exists() or not carpeta.is_dir():
        mensaje = f"Carpeta de demo inválida: {carpeta}"
        print(mensaje)
        return "", mensaje

    print(f"Publicando en Vercel: {nombre_proyecto}")
    deploy = _ejecutar(["vercel", "--prod", "--yes"], cwd=carpeta)
    salida = "\n".join([deploy.stdout or "", deploy.stderr or ""])
    if deploy.returncode != 0:
        error = _mensaje_error(deploy)
        if "login" in error.lower() or "not authenticated" in error.lower() or "unauthorized" in error.lower():
            error = "Debes iniciar sesión con: vercel login"
        print(f"No se pudo hacer deploy en Vercel: {error}")
        return "", error

    url = _extraer_url(salida)
    if not url:
        error = "No se pudo capturar la URL final del deploy de Vercel."
        print(error)
        return "", error
    print(f"Deploy Vercel creado: {url}")
    return url, ""
