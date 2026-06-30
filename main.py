
"""
main.py
Punto de entrada del proyecto.

Ejecución manual:
    python main.py
"""

from agent import ejecutar_agente
from prompts import USER_OBJECTIVE


if __name__ == "__main__":

    print("====================================")
    print(" MI AGENTE ESTADÍSTICO - INICIO")
    print("====================================")

    resultado = ejecutar_agente(objetivo=USER_OBJECTIVE)

    print("\n==============================")
    print("RESULTADO FINAL DEL AGENTE")
    print("==============================")
    print("Éxito:", resultado.success)
    print("Mensaje:", resultado.message)
    print("Excel generado:", resultado.excel_path)
    print("Nota de prensa:", resultado.press_note_url)
    print("Próxima publicación:", resultado.next_publication)
    print("Email enviado/simulado:", resultado.email_sent)
    print("Filas procesadas:", resultado.rows)

    print("====================================")
    print(" PROCESO FINALIZADO")
    print("====================================")
