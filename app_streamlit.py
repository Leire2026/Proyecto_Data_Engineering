"""
app_streamlit.py

Interfaz sencilla en Streamlit para ejecutar Mi Agente Estadístico.

Esta app NO modifica la lógica del agente.
Solo llama a la función ejecutar_agente() definida en agent.py.
"""

import streamlit as st
from pathlib import Path

from agent import ejecutar_agente
from prompts import USER_OBJECTIVE


st.set_page_config(
    page_title="Mi Agente Estadístico",
    page_icon="📊",
    layout="centered"
)

st.title("📊 Mi Agente Estadístico")

st.markdown(
    """
    Esta aplicación ejecuta el agente encargado de descargar los últimos datos completos
    del IPC nacional por grupos ECOICOP desde el INE, generar un archivo Excel,
    incorporar la nota de prensa configurada, identificar la próxima publicación
    prevista y enviar la información por email.
    """
)

st.info(
    "Pulsa el botón para ejecutar el agente. El proceso puede tardar unos segundos."
)

if st.button("🚀 Ejecutar agente", type="primary"):

    with st.spinner("Ejecutando Mi Agente Estadístico..."):
        resultado = ejecutar_agente(objetivo=USER_OBJECTIVE)

    st.subheader("Resultado de la ejecución")

    if resultado.success:
        st.success("El agente ha finalizado correctamente.")
    else:
        st.error("El agente no ha podido completar el proceso.")

    st.write("**Mensaje:**", resultado.message)
    st.write("**Filas procesadas:**", resultado.rows)
    st.write("**Email enviado/simulado:**", resultado.email_sent)

    if resultado.press_note_url:
        st.write("**Nota de prensa:**", resultado.press_note_url)
    else:
        st.write("**Nota de prensa:** no configurada.")

    if resultado.next_publication:
        st.write("**Próxima publicación prevista:**")
        st.json(resultado.next_publication)
    else:
        st.write("**Próxima publicación prevista:** no disponible.")

    if resultado.excel_path:
        excel_path = Path(resultado.excel_path)

        if excel_path.exists():
            st.write("**Archivo Excel generado:**", excel_path.name)

            with open(excel_path, "rb") as file:
                st.download_button(
                    label="📥 Descargar Excel",
                    data=file,
                    file_name=excel_path.name,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.warning("El agente indica que se generó un Excel, pero no se encuentra el archivo.")
    else:
        st.warning("No se ha generado ningún archivo Excel.")
else:
    st.write("Esperando ejecución del agente.")
