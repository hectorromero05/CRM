import pandas as pd

from buscar_maps import agregar_prospecto_desde_maps_url, buscar_prospectos, generar_busquedas, imprimir_resumen_prospecto
from crm_utils import ESTADOS, NICHOS, ZONAS, asegurar_excel, guardar_excel
from generar_demo import generar_demos_lote, prospectos_para_demo_lote
from project_factory import crear_proyecto_cliente, finalizar_proyecto


def ver(df=None, filtro=None):
    df = asegurar_excel() if df is None else df
    if filtro:
        df = df.query(filtro)
    if df.empty:
        print("No hay prospectos para mostrar.")
        return
    columnas = ["ID", "Nombre", "Nicho", "Telefono", "Tiene_web", "Rating", "Resenas", "Prioridad", "Estado", "Demo"]
    print(df[columnas].to_string(index=False))


def buscar_nuevos():
    print("Nichos disponibles:", ", ".join(NICHOS))
    nichos_txt = input("Nichos separados por coma (Enter = todos): ").strip()
    nichos = [x.strip() for x in nichos_txt.split(",") if x.strip()] or NICHOS
    print("Zonas disponibles:", ", ".join(ZONAS))
    zonas_txt = input("Zonas separadas por coma (Enter = todas): ").strip()
    zonas = [x.strip() for x in zonas_txt.split(",") if x.strip()] or ZONAS
    maximo = input("Máximo por búsqueda (Enter = 40): ").strip()
    maximo = int(maximo) if maximo.isdigit() else 40
    buscar_prospectos(generar_busquedas(nichos, zonas), maximo)


def agregar_prospecto_maps_url_cli():
    url = input("Link de Google Maps del negocio: ").strip()
    if not url:
        print("No se ingresó ningún link.")
        return
    try:
        resultado = agregar_prospecto_desde_maps_url(url)
    except Exception as exc:
        print(f"No se pudo agregar el prospecto: {exc}")
        return
    if resultado.get("nuevo"):
        print(f"Prospecto nuevo guardado con ID {resultado.get('id')}.")
    elif resultado.get("actualizado"):
        print(f"Prospecto existente actualizado con ID {resultado.get('id')}.")
    else:
        print(f"Prospecto existente sin cambios con ID {resultado.get('id')}.")
    imprimir_resumen_prospecto(resultado.get("registro", {}))


def cambiar_estado():
    df = asegurar_excel()
    ver(df)
    idp = input("ID a modificar: ").strip()
    if idp not in set(df["ID"].astype(str)):
        print("ID no encontrado.")
        return
    for i, estado in enumerate(ESTADOS, 1):
        print(f"{i}. {estado}")
    sel = input("Nuevo estado (número o texto): ").strip()
    nuevo = ESTADOS[int(sel) - 1] if sel.isdigit() and 1 <= int(sel) <= len(ESTADOS) else sel
    df.loc[df["ID"].astype(str) == idp, "Estado"] = nuevo
    guardar_excel(df)
    print("Estado actualizado.")


def agregar_demo():
    df = asegurar_excel()
    ver(df)
    idp = input("ID: ").strip()
    demo = input("Link o ruta de demo: ").strip()
    mask = df["ID"].astype(str) == idp
    if not mask.any():
        print("ID no encontrado.")
        return
    df.loc[mask, "Demo"] = demo
    df.loc[mask, "Estado"] = "Demo enviada"
    guardar_excel(df)
    print("Demo guardada.")


def crear_proyecto_cliente_cli():
    df = asegurar_excel()
    ver(df)
    idp = input("ID del prospecto para crear proyecto del cliente: ").strip()
    crear_proyecto_cliente(idp)


def finalizar_proyecto_cli():
    df = asegurar_excel()
    ver(df)
    idp = input("ID del prospecto para finalizar proyecto: ").strip()
    finalizar_proyecto(idp)


def generar_demos_en_lote():
    df = asegurar_excel()
    candidatos = prospectos_para_demo_lote(df)
    columnas = ["ID", "Nombre", "Nicho", "Telefono", "Rating", "Resenas", "Direccion"]
    if candidatos.empty:
        print("No hay prospectos de prioridad alta, estado Pendiente/Contactado y sin demo todavía.")
        return

    print("Prospectos disponibles para generar demos en lote:")
    print(candidatos[columnas].to_string(index=False))
    ids_txt = input("IDs separados por coma (ejemplo: 201,205,208,214): ").strip()
    ids = [idp.strip() for idp in ids_txt.split(",") if idp.strip()]
    if not ids:
        print("No se ingresaron IDs.")
        return

    ids_validos = set(candidatos["ID"].astype(str))
    ids_filtrados = []
    omitidos = []
    for idp in ids:
        if idp in ids_validos:
            ids_filtrados.append(idp)
        else:
            omitidos.append({"id": idp, "error": "No cumple filtros o no existe."})

    resultado = generar_demos_lote(ids_filtrados)
    creadas = resultado["creadas"]
    fallidas = omitidos + resultado["fallidas"]

    print("\nResumen de generación en lote")
    print(f"Demos creadas: {len(creadas)}")
    for demo in creadas:
        print(f"- ID {demo['id']}")
        print(f"  Carpeta: {demo['carpeta']}")
        print(f"  Prompt: {demo['prompt']}")

    print(f"Demos fallidas: {len(fallidas)}")
    for fallo in fallidas:
        print(f"- ID {fallo['id']}: {fallo['error']}")


def exportar_filtrada():
    df = asegurar_excel()
    df["Resenas"] = pd.to_numeric(df["Resenas"], errors="coerce").fillna(0).astype(int)
    prioridad = input("Prioridad a exportar (Alta/Media/Baja, Enter = todas): ").strip()
    estado = input("Estado a exportar (Enter = todos): ").strip()
    if prioridad:
        df = df[df["Prioridad"].astype(str).str.lower() == prioridad.lower()]
    if estado:
        df = df[df["Estado"].astype(str).str.lower() == estado.lower()]
    salida = input("Nombre de archivo (Enter = export_prospectos.xlsx): ").strip() or "export_prospectos.xlsx"
    df.to_excel(salida, index=False)
    print(f"Exportado: {salida} ({len(df)} registros)")


def menu():
    asegurar_excel()
    while True:
        print("""
CRM Restaurantes
1. Buscar nuevos prospectos
2. Ver prospectos
3. Prospectos Alta prioridad
4. Cambiar estado
5. Exportar Excel
6. Crear proyecto del cliente
7. Finalizar proyecto
8. Generar demos en lote
9. Agregar prospecto por link de Google Maps
10. Configuración
11. Salir
""")
        op = input("Elige una opción: ").strip()
        if op == "1": buscar_nuevos()
        elif op == "2": ver()
        elif op == "3": ver(filtro="Prioridad == 'Alta'")
        elif op == "4": cambiar_estado()
        elif op == "5": exportar_filtrada()
        elif op == "6": crear_proyecto_cliente_cli()
        elif op == "7": finalizar_proyecto_cli()
        elif op == "8": generar_demos_en_lote()
        elif op == "9": agregar_prospecto_maps_url_cli()
        elif op == "10": print("Configura rutas y credenciales desde app.py o config.json.")
        elif op == "11": break
        else: print("Opción no válida.")


if __name__ == "__main__":
    menu()
