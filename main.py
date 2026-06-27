from buscar_maps import buscar_prospectos, generar_busquedas
from crm_utils import ESTADOS, NICHOS, ZONAS, asegurar_excel, guardar_excel
from generar_demo import generar_demo


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


def exportar_filtrada():
    df = asegurar_excel()
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
3. Ver prospectos de prioridad alta
4. Cambiar estado
5. Agregar link de demo
6. Generar demo para un prospecto
7. Exportar lista filtrada
8. Salir
""")
        op = input("Elige una opción: ").strip()
        if op == "1": buscar_nuevos()
        elif op == "2": ver()
        elif op == "3": ver(filtro="Prioridad == 'Alta'")
        elif op == "4": cambiar_estado()
        elif op == "5": agregar_demo()
        elif op == "6": generar_demo()
        elif op == "7": exportar_filtrada()
        elif op == "8": break
        else: print("Opción no válida.")


if __name__ == "__main__":
    menu()
