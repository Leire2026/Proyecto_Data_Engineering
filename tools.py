"""
tools.py
Herramientas operativas que puede usar el agente:
- consultar datos del IPC en la API del INE
- transformar los datos en un DataFrame
- crear un Excel
- obtener la nota de prensa configurada
- obtener la próxima publicación prevista
- crear y enviar el email
"""

from __future__ import annotations

import mimetypes
import smtplib
from dataclasses import dataclass
from datetime import date, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
import requests

import config


@dataclass
class AgentResult:
    """Resultado final simplificado del agente."""

    success: bool
    message: str
    excel_path: Optional[str] = None
    press_note_url: Optional[str] = None
    next_publication: Optional[Dict[str, str]] = None
    email_sent: bool = False
    rows: int = 0


class ApiCallCounter:
    """Control sencillo para no superar el límite de llamadas a APIs."""

    def __init__(self, max_calls: int):
        self.max_calls = max_calls
        self.calls = 0

    def check(self):
        if self.calls >= self.max_calls:
            raise RuntimeError(f"Se ha superado el límite de {self.max_calls} llamadas a la API.")
        self.calls += 1


api_counter = ApiCallCounter(config.MAX_API_CALLS)


MESES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def consultar_datos_ipc(nult: int = config.NULT) -> List[Dict[str, Any]]:
    """Consulta los últimos datos de la tabla IPC 50902 en la API oficial del INE."""
    api_counter.check()
    url = f"{config.INE_API_BASE_URL}/DATOS_TABLA/{config.IPC_TABLE_ID}"
    params = {"nult": nult}
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("La API del INE no ha devuelto una lista de series.")
    return data


def _normalizar_texto(texto: str) -> str:
    return " ".join(str(texto).replace("\n", " ").split())


def _detectar_tipo_dato(nombre_serie: str) -> str:
    """Detecta si una serie es índice, variación mensual o variación anual."""
    nombre = _normalizar_texto(nombre_serie).lower()

    # Excluimos variables fuera del alcance del proyecto.
    if "variación en lo que va de año" in nombre or "variacion en lo que va de año" in nombre:
        return "No identificado"
    if "variación mensual" in nombre or "variacion mensual" in nombre:
        return "Variación mensual"
    if "variación anual" in nombre or "variacion anual" in nombre:
        return "Variación anual"
    if nombre.endswith("índice.") or nombre.endswith("indice.") or " índice." in nombre or " indice." in nombre:
        return "Índice"

    return "No identificado"


def _extraer_grupo_ecoicop(nombre_serie: str) -> str:
    """Extrae el grupo ECOICOP desde nombres como 'Nacional. Transporte. Índice'."""
    texto = _normalizar_texto(nombre_serie)
    partes = [p.strip() for p in texto.split(".") if p.strip()]

    # En la tabla 50902 suele ser: Nacional. Grupo ECOICOP. Tipo de dato.
    if len(partes) >= 3 and partes[0].lower() == "nacional":
        return partes[1]
    if len(partes) >= 2:
        return partes[0]
    return texto or "Grupo no identificado"


def _periodo_desde_dato(dato: Dict[str, Any]) -> Optional[str]:
    periodo = dato.get("NombrePeriodo") or dato.get("T3_Periodo") or dato.get("Periodo")
    if periodo:
        return str(periodo)
    fk_periodo = dato.get("FK_Periodo")
    try:
        return MESES.get(int(fk_periodo), str(fk_periodo))
    except (TypeError, ValueError):
        return None


def _fecha_desde_milisegundos(valor: Any) -> Optional[str]:
    try:
        if valor is None:
            return None
        return datetime.fromtimestamp(int(valor) / 1000).date().isoformat()
    except (TypeError, ValueError, OSError):
        return None


def transformar_ipc_json_a_dataframe(raw_data: List[Dict[str, Any]]) -> pd.DataFrame:
    """Convierte el JSON de la API del INE en un DataFrame de pandas."""
    filas = []

    for serie in raw_data:
        serie_id = serie.get("COD") or serie.get("Id") or serie.get("cod")
        nombre_serie = serie.get("Nombre") or serie.get("nombre") or ""
        datos = serie.get("Data") or serie.get("Datos") or serie.get("datos") or []

        tipo_dato = _detectar_tipo_dato(nombre_serie)
        grupo_ecoicop = _extraer_grupo_ecoicop(nombre_serie)

        # Nos quedamos solo con las tres variables del alcance del proyecto.
        if tipo_dato not in {"Índice", "Variación mensual", "Variación anual"}:
            continue

        for dato in datos:
            filas.append(
                {
                    "serie_id": serie_id,
                    "nombre_serie": _normalizar_texto(nombre_serie),
                    "grupo_ecoicop": grupo_ecoicop,
                    "tipo_dato": tipo_dato,
                    "periodo": _periodo_desde_dato(dato),
                    "anyo": dato.get("Anyo") or dato.get("Año"),
                    "fecha": _fecha_desde_milisegundos(dato.get("Fecha")),
                    "valor": dato.get("Valor"),
                }
            )

    df = pd.DataFrame(filas)
    if df.empty:
        return df

    df["valor"] = pd.to_numeric(df["valor"], errors="coerce")

    # ------------------------------------------------------------
    # Selección del último periodo completo
    # ------------------------------------------------------------
    # En la tabla actual del IPC puede existir un "avance" del mes más reciente
    # que solo incluye el índice general y no todos los grupos ECOICOP.
    # Para evitar que el agente genere un Excel incompleto, descargamos varios
    # periodos con NULT y nos quedamos con el último periodo que tenga más de
    # 30 filas. Un periodo completo debería incluir los grupos ECOICOP y los
    # tres tipos de dato del alcance del proyecto: índice, variación mensual
    # y variación anual.
    df["periodo_completo"] = (
        df["anyo"].astype(str).str.strip()
        + "_"
        + df["periodo"].astype(str).str.strip()
    )

    conteo_periodos = (
        df.groupby("periodo_completo", dropna=False)
        .size()
        .reset_index(name="num_filas")
    )

    periodos_validos = conteo_periodos[conteo_periodos["num_filas"] > 30]

    if not periodos_validos.empty:
        ultimo_periodo_valido = periodos_validos.iloc[-1]["periodo_completo"]
        df = df[df["periodo_completo"] == ultimo_periodo_valido].copy()

    df = df.drop(columns=["periodo_completo"])
    df = df.sort_values(["grupo_ecoicop", "tipo_dato"]).reset_index(drop=True)
    return df


def crear_excel_ipc(df: pd.DataFrame, output_dir: Path = config.OUTPUT_DIR) -> Path:
    """Genera un Excel con los datos del IPC en formato largo y tabla resumen."""
    if df.empty:
        raise ValueError("No se puede generar Excel porque el DataFrame está vacío.")

    output_dir.mkdir(exist_ok=True)
    fecha_actual = datetime.now().strftime("%Y%m%d_%H%M")
    excel_path = output_dir / f"ipc_ecoicop_{fecha_actual}.xlsx"

    tabla_resumen = df.pivot_table(
        index=["grupo_ecoicop", "periodo", "anyo"],
        columns="tipo_dato",
        values="valor",
        aggfunc="first",
    ).reset_index()

    orden_columnas = [
        "grupo_ecoicop", "periodo", "anyo", "Índice", "Variación mensual", "Variación anual"
    ]
    tabla_resumen = tabla_resumen[[c for c in orden_columnas if c in tabla_resumen.columns]]

    with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="datos_largos", index=False)
        tabla_resumen.to_excel(writer, sheet_name="tabla_resumen", index=False)

        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column_cells in worksheet.columns:
                length = max(len(str(cell.value)) if cell.value is not None else 0 for cell in column_cells)
                worksheet.column_dimensions[column_cells[0].column_letter].width = min(length + 2, 60)

    return excel_path


def obtener_nota_prensa_ipc() -> Optional[str]:
    """Devuelve la URL de la nota de prensa configurada en .env."""
    return config.PRESS_NOTE_URL if config.PRESS_NOTE_URL else None


def obtener_proxima_publicacion(today: Optional[date] = None) -> Optional[Dict[str, str]]:
    """Obtiene la próxima fecha prevista de publicación del IPC desde el calendario configurado."""
    if today is None:
        today = date.today()

    for item in config.IPC_PUBLICATION_CALENDAR_2026:
        fecha = datetime.strptime(item["fecha_publicacion"], "%Y-%m-%d").date()
        if fecha >= today:
            return item

    return None


def resumir_datos_basicos(df: pd.DataFrame) -> Dict[str, Any]:
    """Crea un resumen sencillo de los datos descargados."""
    if df.empty:
        return {"filas": 0, "periodos": [], "anyos": [], "tipos_dato": [], "grupos": 0}

    return {
        "filas": int(len(df)),
        "periodos": sorted(df["periodo"].dropna().astype(str).unique().tolist()),
        "anyos": sorted(df["anyo"].dropna().astype(str).unique().tolist()),
        "tipos_dato": sorted(df["tipo_dato"].dropna().astype(str).unique().tolist()),
        "grupos": int(df["grupo_ecoicop"].nunique()),
    }


def crear_cuerpo_email(
    resumen: Dict[str, Any],
    excel_path: Path,
    press_note_url: Optional[str],
    next_publication: Optional[Dict[str, str]],
) -> str:
    """Crea el cuerpo del email mensual."""
    lineas = [
        "Hola,",
        "",
        "Se adjunta el archivo Excel con los últimos datos disponibles del IPC nacional por grupos ECOICOP publicados por el INE.",
        "",
        "Resumen de la descarga:",
        f"- Filas descargadas: {resumen.get('filas', 0)}",
        f"- Periodos incluidos: {', '.join(resumen.get('periodos', []))}",
        f"- Años incluidos: {', '.join(resumen.get('anyos', []))}",
        f"- Tipos de dato: {', '.join(resumen.get('tipos_dato', []))}",
        f"- Número de grupos ECOICOP: {resumen.get('grupos', 0)}",
        "",
        f"Archivo generado: {excel_path.name}",
    ]

    if press_note_url:
        lineas.append(f"Nota de prensa oficial del INE: {press_note_url}")
    else:
        lineas.append("Nota de prensa oficial del INE: no configurada para esta ejecución.")

    if next_publication:
        lineas.append(
            f"Próxima publicación prevista del IPC: {next_publication['fecha_publicacion']} "
            f"({next_publication['periodo_referencia']})."
        )
    else:
        lineas.append("Próxima publicación prevista del IPC: no disponible en el calendario configurado.")

    lineas.extend(["", "Fuente: Instituto Nacional de Estadística (INE).", "", "Un saludo."])
    return "\n".join(lineas)


def enviar_email(asunto: str, cuerpo: str, adjuntos: Optional[List[Path]] = None) -> bool:
    """Envía un email con adjuntos o simula el envío si EMAIL_DRY_RUN=True."""
    adjuntos = adjuntos or []

    if not config.EMAIL_TO:
        print("No hay destinatarios configurados en EMAIL_TO. No se envía email.")
        return False

    if config.EMAIL_DRY_RUN:
        print("\n=== MODO PRUEBA: EMAIL_DRY_RUN=True ===")
        print("Para:", ", ".join(config.EMAIL_TO))
        print("Asunto:", asunto)
        print("Cuerpo:\n", cuerpo)
        print("Adjuntos:", [str(a) for a in adjuntos])
        print("=== FIN MODO PRUEBA ===\n")
        return True

    if not config.SMTP_USER or not config.SMTP_PASSWORD:
        raise ValueError("Faltan SMTP_USER/EMAIL_USER o SMTP_PASSWORD/EMAIL_PASSWORD en el archivo .env.")

    msg = EmailMessage()
    msg["Subject"] = asunto
    msg["From"] = config.EMAIL_FROM
    msg["To"] = ", ".join(config.EMAIL_TO)
    msg.set_content(cuerpo)

    for path in adjuntos:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"No existe el adjunto: {path}")

        mime_type, _ = mimetypes.guess_type(path)
        if mime_type is None:
            mime_type = "application/octet-stream"

        maintype, subtype = mime_type.split("/", 1)
        with open(path, "rb") as f:
            msg.add_attachment(f.read(), maintype=maintype, subtype=subtype, filename=path.name)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)

    return True
