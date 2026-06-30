"""
config.py
Configuración central del proyecto "Mi Agente Estadístico".

IMPORTANTE:
- No escribas claves ni contraseñas reales en este archivo.
- Usa un archivo .env en esta misma carpeta.
"""

from pathlib import Path
import os
from dotenv import load_dotenv

# Directorio base del proyecto
BASE_DIR = Path(__file__).resolve().parent

# Cargar explícitamente el .env situado junto a este archivo
load_dotenv(dotenv_path=BASE_DIR / ".env")


def _env_bool(nombre: str, default: str = "False") -> bool:
    """Convierte una variable de entorno a booleano."""
    valor = os.getenv(nombre, default).strip().lower()
    return valor in {"1", "true", "yes", "y", "si", "sí"}


def _env_int(nombre: str, default: str) -> int:
    """Convierte una variable de entorno a entero con valor por defecto."""
    try:
        return int(os.getenv(nombre, default))
    except ValueError:
        return int(default)


# =========================
# CONFIGURACIÓN GENERAL
# =========================

PROJECT_NAME = "Mi Agente Estadístico"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

# =========================
# CONFIGURACIÓN GROQ
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant").strip()
MAX_AGENT_STEPS = _env_int("MAX_AGENT_STEPS", "10")

# =========================
# CONFIGURACIÓN API INE
# =========================

INE_API_BASE_URL = "https://servicios.ine.es/wstempus/js/ES"


# Tabla INE: Índices nacionales: general y de grupos ECOICOP ver.2.
# Link orientativo: https://www.ine.es/jaxiT3/Tabla.htm?t=76125
IPC_TABLE_ID = os.getenv("IPC_TABLE_ID", "76125").strip()

# Número de últimos datos a descargar por serie.
NULT = _env_int("NULT", "3")

# Límite de seguridad de llamadas a APIs por ejecución.
MAX_API_CALLS = _env_int("MAX_API_CALLS", "20")

# =========================
# NOTA DE PRENSA
# =========================

# Para evitar scraping, la nota de prensa se configura manualmente.
# Ejemplo: https://www.ine.es/dyngs/Prensa/IPC0526.htm  
PRESS_NOTE_URL = os.getenv("PRESS_NOTE_URL", "").strip()

# =========================
# CALENDARIO IPC 2026
# =========================

IPC_PUBLICATION_CALENDAR_2026 = [
    {"fecha_publicacion": "2026-01-15", "periodo_referencia": "Diciembre 2025"},
    {"fecha_publicacion": "2026-02-13", "periodo_referencia": "Enero 2026"},
    {"fecha_publicacion": "2026-03-13", "periodo_referencia": "Febrero 2026"},
    {"fecha_publicacion": "2026-04-14", "periodo_referencia": "Marzo 2026"},
    {"fecha_publicacion": "2026-05-14", "periodo_referencia": "Abril 2026"},
    {"fecha_publicacion": "2026-06-12", "periodo_referencia": "Mayo 2026"},
    {"fecha_publicacion": "2026-07-15", "periodo_referencia": "Junio 2026"},
    {"fecha_publicacion": "2026-08-13", "periodo_referencia": "Julio 2026"},
    {"fecha_publicacion": "2026-09-15", "periodo_referencia": "Agosto 2026"},
    {"fecha_publicacion": "2026-10-14", "periodo_referencia": "Septiembre 2026"},
    {"fecha_publicacion": "2026-11-13", "periodo_referencia": "Octubre 2026"},
    {"fecha_publicacion": "2026-12-15", "periodo_referencia": "Noviembre 2026"},
]

# =========================
# CONFIGURACIÓN EMAIL
# =========================

# True = no envía correo real. False = envía correo real.
EMAIL_DRY_RUN = _env_bool("EMAIL_DRY_RUN", "True")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
SMTP_PORT = _env_int("SMTP_PORT", "587")

# Acepta tanto nombres SMTP_* como EMAIL_* para evitar errores de configuración.
SMTP_USER = os.getenv("SMTP_USER", os.getenv("EMAIL_USER", "")).strip()
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", os.getenv("EMAIL_PASSWORD", "")).strip()
EMAIL_FROM = os.getenv("EMAIL_FROM", SMTP_USER).strip()

_raw_email_to = os.getenv("EMAIL_TO", "")
EMAIL_TO = [email.strip() for email in _raw_email_to.replace(";", ",").split(",") if email.strip()]
