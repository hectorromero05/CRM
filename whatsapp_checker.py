import shutil
from datetime import datetime
from pathlib import Path

from crm_utils import ARCHIVO_EXCEL, asegurar_excel, guardar_excel, normalizar_telefono

WHATSAPP_SI = "Sí"
WHATSAPP_NO = "No"
WHATSAPP_ERROR = "Error"
WHATSAPP_PENDIENTE = "Pendiente"
PERFIL_WHATSAPP = Path(".whatsapp_profile")


def normalizar_telefono_whatsapp(telefono):
    """Devuelve teléfono en formato internacional para enlaces wa.me.

    Por defecto asume México: 10 dígitos locales => 52XXXXXXXXXX.
    """
    digitos = normalizar_telefono(telefono)
    if not digitos:
        return ""
    if digitos.startswith("00"):
        digitos = digitos[2:]
    if len(digitos) == 10:
        return f"52{digitos}"
    if len(digitos) == 11 and digitos.startswith("1"):
        return f"52{digitos[-10:]}"
    if len(digitos) == 12 and digitos.startswith("52"):
        return digitos
    if len(digitos) == 13 and digitos.startswith("521"):
        return f"52{digitos[-10:]}"
    return digitos


def url_whatsapp(telefono):
    numero = normalizar_telefono_whatsapp(telefono)
    return f"https://wa.me/{numero}" if numero else ""


def _asegurar_columnas_whatsapp(df):
    for columna in ["WhatsApp", "Fecha_Verificacion_WhatsApp", "Error_WhatsApp"]:
        if columna not in df.columns:
            df[columna] = ""
    df["WhatsApp"] = df["WhatsApp"].fillna("").replace("", WHATSAPP_PENDIENTE)
    return df


def reiniciar_sesion_whatsapp():
    """Renombra de forma segura el perfil antiguo de WhatsApp Web si existe."""
    if not PERFIL_WHATSAPP.exists():
        return None
    destino = PERFIL_WHATSAPP.with_name(f"{PERFIL_WHATSAPP.name}.bak-{datetime.now().strftime('%Y%m%d-%H%M%S')}")
    shutil.move(str(PERFIL_WHATSAPP), str(destino))
    return destino


def verificar_whatsapp_por_id(id_prospecto, forzar=False):
    return verificar_whatsapp_lote(ids=[str(id_prospecto)], maximo=1, forzar=forzar)


def verificar_whatsapp_lote(maximo=10, prioridad=None, estado=None, whatsapp_estado=WHATSAPP_PENDIENTE, ids=None, forzar=False):
    """Verificación automática desactivada.

    WhatsApp ya no se automatiza con Playwright. Usa la sección de Streamlit
    "Verificación manual asistida", que abre enlaces wa.me y permite guardar
    manualmente Sí/No/Error en el Excel.
    """
    df = _asegurar_columnas_whatsapp(asegurar_excel(ARCHIVO_EXCEL))
    guardar_excel(df, ARCHIVO_EXCEL)
    raise RuntimeError(
        "La verificación automática con Playwright está desactivada. "
        "Usa la sección 'Verificación manual asistida' en app.py."
    )
