"""Automatización para crear y finalizar proyectos web de restaurantes."""
import base64
import os
import shutil
import subprocess
import time
import webbrowser
from datetime import datetime
from pathlib import Path

from codex_manager import _abrir_vscode, _copiar_portapapeles, asegurar_archivos_codex
from crm_utils import ARCHIVO_EXCEL, CLIENTES_DEFAULT, PLANTILLA_DEFAULT, asegurar_excel, carpeta_unica, guardar_excel, slugify
from generar_demo import generar_demo
from vercel_manager import _extraer_url

HEREDADAS = [".git", ".vercel", "node_modules", "dist"]
PNG_1X1 = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII=")
JPG_1X1 = base64.b64decode("/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAP//////////////////////////////////////////////////////////////////////////////////////2wBDAf//////////////////////////////////////////////////////////////////////////////////////wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIQAxAAAAF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABBQJ//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAwEBPwF//8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAgBAgEBPwF//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQAGPwJ//8QAFBABAAAAAAAAAAAAAAAAAAAAAP/aAAgBAQABPyF//9k=")


def _run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=str(cwd) if cwd else None, text=True, capture_output=True, check=False)


def _msg(res):
    return (res.stderr or res.stdout or "Error desconocido").strip()


def _cmd_disponible(nombre):
    """Devuelve el ejecutable disponible, prefiriendo .cmd en Windows."""
    cmd = shutil.which(f"{nombre}.cmd")
    normal = shutil.which(nombre)
    if os.name == "nt":
        return cmd or normal
    return normal or cmd


def _imprimir_salida(res):
    if res.stdout:
        print(res.stdout)
    if res.stderr:
        print(res.stderr)


def _note(df, idx, text):
    prev = str(df.at[idx, "Notas"] or "").strip() if "Notas" in df.columns else ""
    df.at[idx, "Notas"] = f"{prev}\n{text}".strip() if prev else text


def eliminar_heredadas(carpeta):
    for nombre in HEREDADAS:
        objetivo = Path(carpeta) / nombre
        if objetivo.exists():
            shutil.rmtree(objetivo, ignore_errors=True)


def crear_placeholders(public_dir):
    public_dir = Path(public_dir)
    public_dir.mkdir(parents=True, exist_ok=True)
    for name in ["hero.jpg", "galeria1.jpg", "galeria2.jpg", "galeria3.jpg"]:
        p = public_dir / name
        if not p.exists():
            p.write_bytes(JPG_1X1)
    logo = public_dir / "logo.png"
    if not logo.exists():
        logo.write_bytes(PNG_1X1)


def _github_user():
    res = _run(["gh", "api", "user", "--jq", ".login"])
    return res.stdout.strip() if res.returncode == 0 else ""


def _repo_exists(owner, name):
    return _run(["gh", "repo", "view", f"{owner}/{name}"]).returncode == 0


def _available_repo(owner, base):
    if not _repo_exists(owner, base):
        return base
    i = 2
    while _repo_exists(owner, f"{base}-{i}"):
        i += 1
    return f"{base}-{i}"


def _git_clean_push(carpeta, repo_name):
    owner = _github_user()
    if not owner:
        return "", "No se pudo obtener usuario GitHub. Ejecuta gh auth login."
    repo_name = _available_repo(owner, repo_name)
    repo_url = f"https://github.com/{owner}/{repo_name}"
    for cmd in (["git", "init"], ["git", "add", "."], ["git", "commit", "-m", "Crear proyecto del cliente"], ["git", "branch", "-M", "main"]):
        res = _run(cmd, cwd=carpeta)
        if res.returncode != 0:
            return "", f"Error {' '.join(cmd)}: {_msg(res)}"
    res = _run(["gh", "repo", "create", repo_name, "--public"], cwd=carpeta)
    if res.returncode != 0:
        return "", f"Error al crear repo GitHub: {_msg(res)}"
    res = _run(["git", "remote", "add", "origin", f"{repo_url}.git"], cwd=carpeta)
    if res.returncode != 0:
        return "", f"Error al agregar remote: {_msg(res)}"
    res = _run(["git", "push", "-u", "origin", "main"], cwd=carpeta)
    if res.returncode != 0:
        return "", f"Error al hacer push: {_msg(res)}"
    return repo_url, ""


def crear_proyecto_cliente(id_prospecto, plantilla=PLANTILLA_DEFAULT, clientes=CLIENTES_DEFAULT, archivo=ARCHIVO_EXCEL):
    start = time.time(); idp = str(id_prospecto).strip(); df = asegurar_excel(archivo)
    fila = df[df["ID"].astype(str) == idp]
    if fila.empty:
        print("ID no encontrado."); return None
    idx = fila.index[0]; resumen = {"carpeta": "", "github": "", "codex_task": ""}
    try:
        carpeta = generar_demo(idp, plantilla=plantilla, clientes=clientes, archivo=archivo)
        if not carpeta: return None
        carpeta = Path(carpeta).resolve(); resumen["carpeta"] = str(carpeta)
        eliminar_heredadas(carpeta); crear_placeholders(carpeta / "public")
        archivos = asegurar_archivos_codex(carpeta, asegurar_excel(archivo).loc[idx].to_dict())
        readme = carpeta / "README_CLIENTE.md"
        readme.write_text(f"# Proyecto cliente\n\nProyecto web generado para {fila.iloc[0].get('Nombre','restaurante')}.\n\n- Datos: restaurant.json\n- Tarea Codex: codex_task.md\n", encoding="utf-8")
        resumen["codex_task"] = str(archivos["codex_task"])
        repo, error = _git_clean_push(carpeta, f"{slugify(fila.iloc[0].get('Nombre'))}-web")
        df = asegurar_excel(archivo); idx = df[df["ID"].astype(str) == idp].index[0]
        if repo:
            resumen["github"] = repo; df.at[idx,"Repositorio_GitHub"] = repo; df.at[idx,"URL_GitHub"] = repo; df.at[idx,"Repo_Creado"] = "sí"; df.at[idx,"Estado"] = "Repositorio creado"
        else:
            _note(df, idx, f"Error GitHub: {error}")
        df.at[idx,"Ruta_Local"] = str(carpeta); df.at[idx,"Demo"] = str(carpeta); df.at[idx,"Restaurant_JSON"] = str(archivos["restaurant_json"]); df.at[idx,"Codex_Task"] = str(archivos["codex_task"]); df.at[idx,"Proyecto_Creado"] = "sí"; df.at[idx,"Fecha_Proyecto"] = datetime.now().strftime("%Y-%m-%d %H:%M"); df.at[idx,"Tiempo_Generacion"] = f"{time.time()-start:.1f}s"
        guardar_excel(df, archivo)
        try: _abrir_vscode(carpeta)
        except Exception as exc: print(f"No se pudo abrir VS Code: {exc}")
        try: webbrowser.open("https://chatgpt.com/codex")
        except Exception as exc: print(f"No se pudo abrir Codex: {exc}")
        try: _copiar_portapapeles(Path(archivos["codex_task"]).read_text(encoding="utf-8"), archivos["codex_task"])
        except Exception as exc: print(f"No se pudo copiar al portapapeles: {exc}")
        print("Proyecto listo.\nSeleccione el repositorio en Codex y pegue la tarea.")
        return resumen
    except Exception as exc:
        df = asegurar_excel(archivo); idx = df[df["ID"].astype(str) == idp].index[0]; _note(df, idx, f"Error crear proyecto: {exc}"); guardar_excel(df, archivo); print(exc); return resumen


def finalizar_proyecto(id_prospecto, archivo=ARCHIVO_EXCEL):
    idp = str(id_prospecto).strip(); df = asegurar_excel(archivo); fila = df[df["ID"].astype(str) == idp]
    if fila.empty: print("ID no encontrado."); return None
    idx = fila.index[0]; carpeta = Path(str(fila.iloc[0].get("Ruta_Local") or fila.iloc[0].get("Demo") or "")).expanduser().resolve()
    if not carpeta.exists(): print(f"Ruta local inválida: {carpeta}"); return None
    resumen = {"repositorio": str(fila.iloc[0].get("Repositorio_GitHub") or fila.iloc[0].get("URL_GitHub") or ""), "vercel": "", "ruta": str(carpeta)}

    res = _run(["git", "pull"], cwd=carpeta); _imprimir_salida(res)
    if res.returncode != 0:
        _note(df, idx, f"Error git pull: {_msg(res)}"); guardar_excel(df, archivo); return resumen

    npm = _cmd_disponible("npm")
    if not npm:
        error = "Node.js/npm no está instalado o no está en PATH."
        print(error); _note(df, idx, error); guardar_excel(df, archivo); return resumen

    vercel = _cmd_disponible("vercel")
    if not vercel:
        error = "Vercel CLI no está instalado. Instálalo con npm i -g vercel."
        print(error); _note(df, idx, error); guardar_excel(df, archivo); return resumen

    for cmd in ([npm, "install"], [npm, "run", "build"]):
        res = _run(cmd, cwd=carpeta); _imprimir_salida(res)
        if res.returncode != 0:
            _note(df, idx, f"Error {' '.join(cmd)}: {_msg(res)}"); guardar_excel(df, archivo); return resumen

    res = _run([vercel, "--prod", "--yes"], cwd=carpeta); _imprimir_salida(res)
    if res.returncode != 0:
        _note(df, idx, f"Error vercel: {_msg(res)}"); guardar_excel(df, archivo); return resumen
    url = _extraer_url((res.stdout or "") + "\n" + (res.stderr or "")); resumen["vercel"] = url
    if url:
        df.at[idx,"URL_Vercel"] = url; df.at[idx,"Vercel_URL"] = url; df.at[idx,"Deploy_Completado"] = "sí"; df.at[idx,"Fecha_Deploy"] = datetime.now().strftime("%Y-%m-%d %H:%M"); df.at[idx,"Estado"] = "Demo publicada"; guardar_excel(df, archivo); webbrowser.open(url)
    print(f"Repositorio: {resumen['repositorio']}\nVercel: {url}\nRuta local: {carpeta}")
    return resumen
