"""
agent.py
Implementación del agente con Groq + tool calling.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from groq import Groq

import config
from prompts import SYSTEM_PROMPT, USER_OBJECTIVE
from tools import (
    AgentResult,
    consultar_datos_ipc,
    transformar_ipc_json_a_dataframe,
    crear_excel_ipc,
    obtener_nota_prensa_ipc,
    obtener_proxima_publicacion,
    resumir_datos_basicos,
    crear_cuerpo_email,
    enviar_email,
)


class AgentState:
    """Estado interno del agente durante una ejecución."""

    def __init__(self):
        self.raw_data = None
        self.df = None
        self.excel_path: Optional[Path] = None
        self.press_note_url: Optional[str] = None
        self.next_publication: Optional[Dict[str, str]] = None
        self.resumen: Optional[Dict[str, Any]] = None
        self.email_body: Optional[str] = None
        self.email_sent: bool = False
        self.finished: bool = False
        self.final_message: str = ""
        self.errors: list[str] = []


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "consultar_datos_ipc",
            "description": "Consulta la API oficial del INE para obtener los últimos datos del IPC nacional por grupos ECOICOP.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transformar_datos_ipc",
            "description": "Transforma el JSON descargado del INE en un DataFrame limpio.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_excel_ipc",
            "description": "Crea un archivo Excel con los datos del IPC transformados.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_nota_prensa_ipc",
            "description": "Obtiene la URL de la nota de prensa oficial del INE configurada para esta ejecución.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "obtener_proxima_publicacion",
            "description": "Obtiene la próxima fecha prevista de publicación del IPC según el calendario configurado.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "preparar_email_ipc",
            "description": "Prepara el cuerpo del email mensual del IPC. Requiere que el Excel ya exista.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "enviar_email_ipc",
            "description": "Envía o simula el envío del email del IPC a los destinatarios autorizados.",
            "parameters": {"type": "object", "properties": {}, "required": [], "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finalizar_proceso",
            "description": "Finaliza el proceso del agente cuando el objetivo se ha completado o no puede continuar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mensaje": {
                        "type": "string",
                        "description": "Mensaje final breve explicando el resultado del proceso.",
                    }
                },
                "required": ["mensaje"],
                "additionalProperties": False,
            },
        },
    },
]


def construir_tool_functions(state: AgentState) -> Dict[str, Callable[..., Dict[str, Any]]]:
    """Crea las funciones que podrá ejecutar el agente durante esta ejecución."""

    def tool_consultar_datos_ipc() -> Dict[str, Any]:
        state.raw_data = consultar_datos_ipc()
        return {"ok": True, "mensaje": "Datos del IPC descargados desde la API del INE.", "series_descargadas": len(state.raw_data)}

    def tool_transformar_datos_ipc() -> Dict[str, Any]:
        if state.raw_data is None:
            return {"ok": False, "error": "No hay datos descargados. Ejecuta antes consultar_datos_ipc."}
        state.df = transformar_ipc_json_a_dataframe(state.raw_data)
        if state.df.empty:
            return {"ok": False, "error": "La transformación ha generado un DataFrame vacío."}
        state.resumen = resumir_datos_basicos(state.df)
        return {"ok": True, "mensaje": "Datos transformados correctamente.", "filas": int(len(state.df)), "resumen": state.resumen}

    def tool_crear_excel_ipc() -> Dict[str, Any]:
        if state.df is None or state.df.empty:
            return {"ok": False, "error": "No hay DataFrame válido. Ejecuta antes transformar_datos_ipc."}
        state.excel_path = crear_excel_ipc(state.df)
        return {"ok": True, "mensaje": "Archivo Excel generado correctamente.", "excel_path": str(state.excel_path)}

    def tool_obtener_nota_prensa_ipc() -> Dict[str, Any]:
        state.press_note_url = obtener_nota_prensa_ipc()
        if state.press_note_url:
            return {"ok": True, "mensaje": "Nota de prensa configurada localizada.", "press_note_url": state.press_note_url}
        return {"ok": True, "mensaje": "No hay nota de prensa configurada. El proceso puede continuar.", "press_note_url": None}

    def tool_obtener_proxima_publicacion() -> Dict[str, Any]:
        state.next_publication = obtener_proxima_publicacion()
        return {"ok": True, "mensaje": "Consulta de próxima publicación completada.", "next_publication": state.next_publication}

    def tool_preparar_email_ipc() -> Dict[str, Any]:
        if state.excel_path is None:
            return {"ok": False, "error": "No existe archivo Excel. Ejecuta antes crear_excel_ipc."}
        if state.resumen is None:
            return {"ok": False, "error": "No existe resumen de datos. Ejecuta antes transformar_datos_ipc."}
        state.email_body = crear_cuerpo_email(
            resumen=state.resumen,
            excel_path=state.excel_path,
            press_note_url=state.press_note_url,
            next_publication=state.next_publication,
        )
        return {"ok": True, "mensaje": "Email preparado correctamente.", "asunto": "Actualización mensual IPC - INE"}

    def tool_enviar_email_ipc() -> Dict[str, Any]:
        if state.email_body is None:
            return {"ok": False, "error": "El email no está preparado. Ejecuta antes preparar_email_ipc."}
        if state.excel_path is None:
            return {"ok": False, "error": "No existe archivo Excel adjunto."}
        state.email_sent = enviar_email(
            asunto="Actualización mensual IPC - INE",
            cuerpo=state.email_body,
            adjuntos=[state.excel_path],
        )
        return {
            "ok": state.email_sent,
            "mensaje": "Email enviado o simulado correctamente." if state.email_sent else "Email no enviado.",
            "email_sent": state.email_sent,
        }

    def tool_finalizar_proceso(mensaje: str) -> Dict[str, Any]:
        state.finished = True
        state.final_message = mensaje
        return {"ok": True, "mensaje": mensaje}

    return {
        "consultar_datos_ipc": tool_consultar_datos_ipc,
        "transformar_datos_ipc": tool_transformar_datos_ipc,
        "crear_excel_ipc": tool_crear_excel_ipc,
        "obtener_nota_prensa_ipc": tool_obtener_nota_prensa_ipc,
        "obtener_proxima_publicacion": tool_obtener_proxima_publicacion,
        "preparar_email_ipc": tool_preparar_email_ipc,
        "enviar_email_ipc": tool_enviar_email_ipc,
        "finalizar_proceso": tool_finalizar_proceso,
    }


def _parse_tool_arguments(raw_arguments: Optional[str]) -> Dict[str, Any]:
    """Convierte los argumentos de una tool en diccionario seguro."""
    if not raw_arguments:
        return {}
    try:
        arguments = json.loads(raw_arguments)
    except json.JSONDecodeError:
        return {}
    if arguments is None:
        return {}
    if not isinstance(arguments, dict):
        return {}
    return arguments


def _message_to_dict(message: Any) -> Dict[str, Any]:
    """Convierte el mensaje de Groq en dict compatible con el historial."""
    if hasattr(message, "model_dump"):
        return message.model_dump(exclude_none=True)
    if isinstance(message, dict):
        return {k: v for k, v in message.items() if v is not None}
    return {"role": "assistant", "content": str(message)}


def ejecutar_agente(objetivo: str = USER_OBJECTIVE) -> AgentResult:
    """Ejecuta Mi Agente Estadístico usando Groq + tool calling."""
    if not config.GROQ_API_KEY:
        return AgentResult(success=False, message="Falta GROQ_API_KEY. Crea un archivo .env con tu clave de Groq.")

    client = Groq(api_key=config.GROQ_API_KEY)
    state = AgentState()
    tool_functions = construir_tool_functions(state)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": objetivo},
    ]

    print("Iniciando Mi Agente Estadístico con Groq + tools...\n")

    for step in range(1, config.MAX_AGENT_STEPS + 1):
        print(f"--- Paso del agente {step} ---")

        response = client.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            tool_choice="auto",
            temperature=0.1,
            max_tokens=900,
        )

        assistant_message = response.choices[0].message
        messages.append(_message_to_dict(assistant_message))

        tool_calls = assistant_message.tool_calls or []

        if not tool_calls:
            final_text = assistant_message.content or "El agente finalizó sin ejecutar más herramientas."
            state.final_message = final_text
            print(final_text)
            break

        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            arguments = _parse_tool_arguments(tool_call.function.arguments)

            print(f"Tool seleccionada por Groq: {tool_name}")

            if tool_name not in tool_functions:
                tool_result = {"ok": False, "error": f"Tool no reconocida: {tool_name}"}
            else:
                try:
                    tool_result = tool_functions[tool_name](**arguments)
                except Exception as e:
                    tool_result = {"ok": False, "error": str(e)}

            if not tool_result.get("ok", False):
                state.errors.append(tool_result.get("error", "Error no especificado"))

            print("Resultado tool:", tool_result.get("mensaje") or tool_result.get("error"))

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_name,
                    "content": json.dumps(tool_result, ensure_ascii=False, default=str),
                }
            )

        if state.finished:
            break

    proceso_completo = bool(state.excel_path and state.email_sent and state.df is not None and len(state.df) > 0)

    if proceso_completo:
        success = True
        message = state.final_message or "Proceso completado correctamente."
    else:
        success = False
        if state.errors:
            message = "El agente no completó el proceso. Errores: " + " | ".join(state.errors)
        else:
            message = state.final_message or "El agente no completó todos los pasos necesarios."

    return AgentResult(
        success=success,
        message=message,
        excel_path=str(state.excel_path) if state.excel_path else None,
        press_note_url=state.press_note_url,
        next_publication=state.next_publication,
        email_sent=state.email_sent,
        rows=int(len(state.df)) if state.df is not None else 0,
    )
