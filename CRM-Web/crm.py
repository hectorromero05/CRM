import os
import pandas as pd
from datetime import datetime

ARCHIVO = "prospectos.xlsx"

COLUMNAS = [
    "Negocio",
    "Nicho",
    "Telefono",
    "Tiene_web",
    "Sitio_web",
    "Rating",
    "Resenas",
    "Google_Maps",
    "Estado",
    "Demo",
    "Notas",
    "Fecha"
]

def crear_archivo():
    if not os.path.exists(ARCHIVO):
        df = pd.DataFrame(columns=COLUMNAS)
        df.to_excel(ARCHIVO, index=False)
        print(f"Archivo creado: {ARCHIVO}")

def agregar_prospecto():
    negocio = input("Nombre del negocio: ")
    nicho = input("Nicho (restaurante, mariscos, taquería, etc.): ")
    telefono = input("Teléfono: ")
    tiene_web = input("¿Tiene página web? (si/no): ")
    sitio_web = input("Sitio web (si no tiene, dejar vacío): ")
    rating = input("Rating en Google: ")
    resenas = input("Número de reseñas: ")
    maps = input("Link de Google Maps: ")
    notas = input("Notas: ")

    nuevo = {
        "Negocio": negocio,
        "Nicho": nicho,
        "Telefono": telefono,
        "Tiene_web": tiene_web,
        "Sitio_web": sitio_web,
        "Rating": rating,
        "Resenas": resenas,
        "Google_Maps": maps,
        "Estado": "Pendiente",
        "Demo": "",
        "Notas": notas,
        "Fecha": datetime.now().strftime("%Y-%m-%d %H:%M")
    }

    df = pd.read_excel(ARCHIVO)
    df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
    df.to_excel(ARCHIVO, index=False)

    print("Prospecto guardado correctamente.")

def ver_prospectos():
    df = pd.read_excel(ARCHIVO)

    if df.empty:
        print("Todavía no hay prospectos.")
        return

    print(df[["Negocio", "Nicho", "Telefono", "Tiene_web", "Rating", "Resenas", "Estado"]])

def cambiar_estado():
    df = pd.read_excel(ARCHIVO)

    if df.empty:
        print("No hay prospectos.")
        return

    print(df[["Negocio", "Estado"]])
    indice = int(input("Número de fila a modificar: "))

    print("""
Estados sugeridos:
1. Pendiente
2. Contactado
3. Respondió
4. Interesado
5. Demo enviada
6. Cotización enviada
7. Cerrado
8. Perdido
""")

    nuevo_estado = input("Nuevo estado: ")
    df.loc[indice, "Estado"] = nuevo_estado
    df.to_excel(ARCHIVO, index=False)

    print("Estado actualizado.")

def agregar_demo():
    df = pd.read_excel(ARCHIVO)

    print(df[["Negocio", "Demo"]])
    indice = int(input("Número de fila: "))
    demo = input("Link de la demo: ")

    df.loc[indice, "Demo"] = demo
    df.loc[indice, "Estado"] = "Demo enviada"
    df.to_excel(ARCHIVO, index=False)

    print("Demo guardada.")

def menu():
    crear_archivo()

    while True:
        print("""
CRM Web

1. Agregar prospecto
2. Ver prospectos
3. Cambiar estado
4. Agregar demo
5. Salir
""")

        opcion = input("Elige una opción: ")

        if opcion == "1":
            agregar_prospecto()
        elif opcion == "2":
            ver_prospectos()
        elif opcion == "3":
            cambiar_estado()
        elif opcion == "4":
            agregar_demo()
        elif opcion == "5":
            print("Saliendo...")
            break
        else:
            print("Opción no válida.")

menu()