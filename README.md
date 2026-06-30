# Mi Agente Estadístico

## Descripción del proyecto

**Mi Agente Estadístico** es un agente de IA desarrollado dentro del Bootcamp de Data Science.

Su objetivo es automatizar la consulta, procesamiento y distribución de información oficial del **Índice de Precios de Consumo (IPC)** publicada por el Instituto Nacional de Estadística (INE) de España.

El agente descarga automáticamente los últimos datos completos del IPC nacional por grupos ECOICOP, genera un archivo Excel, incorpora información complementaria y envía un correo electrónico a los destinatarios autorizados.

---

## ¿Por qué es un agente y no una automatización?

El proyecto utiliza la arquitectura:

```text
LLM (Groq) + Tools + Objetivo + Capacidad de decisión
```

El modelo de lenguaje recibe un objetivo general y decide dinámicamente qué herramienta debe ejecutar en cada momento.

Arquitectura:

```text
Usuario
   ↓
main.py / Streamlit
   ↓
Groq (LLM)
   ↓
Selección de tools
   ↓
Tools Python
   ↓
API INE / Excel / Email
```

---

## Funcionalidades

El agente es capaz de:

- Consultar la API oficial del INE.
- Descargar los últimos datos completos del IPC nacional.
- Filtrar automáticamente periodos incompletos (avances).
- Transformar los datos a un DataFrame de pandas.
- Generar un archivo Excel.
- Incorporar la nota de prensa oficial del INE.
- Obtener la próxima fecha prevista de publicación.
- Preparar un resumen automático.
- Enviar la información por correo electrónico.
- Mostrar los resultados mediante una interfaz Streamlit.

---

## Estructura del proyecto

```text
mi_agente_estadistico/
│
├── main.py                # Ejecución desde terminal
├── app_streamlit.py       # Interfaz visual Streamlit
├── agent.py               # Lógica del agente y Groq
├── tools.py               # Herramientas operativas
├── config.py              # Configuración general
├── prompts.py             # System Prompt y objetivo
├── requirements.txt       # Librerías necesarias
├── .env                   # Variables privadas
├── .env.example           # Plantilla de variables
├── README.md
└── output/                # Excel generados
```

---

## Tecnologías utilizadas

- Python
- Groq
- Llama 3
- Pandas
- Requests
- OpenPyXL
- Streamlit
- SMTP (Gmail)
- python-dotenv

---

## Instalación

Instalar dependencias:

```bash
pip install -r requirements.txt
```

---

## Configuración del archivo `.env`

Crear un archivo `.env` en la raíz del proyecto.

Ejemplo:

```env
GROQ_API_KEY=tu_api_key

SMTP_USER=tu_correo@gmail.com
SMTP_PASSWORD=tu_password_de_aplicacion

EMAIL_FROM=tu_correo@gmail.com
EMAIL_TO=correo1@gmail.com,correo2@gmail.com

EMAIL_DRY_RUN=False

PRESS_NOTE_URL=https://www.ine.es/dyngs/Prensa/IPC0526.htm

MAX_API_CALLS=20
MAX_AGENT_STEPS=10
NULT=3
```

---

## Ejecución desde terminal

```bash
python main.py
```

---

## Ejecución mediante Streamlit

```bash
streamlit run app_streamlit.py
```

---

## Flujo de funcionamiento

1. El usuario ejecuta el agente.
2. Groq recibe el objetivo.
3. Groq decide qué herramienta utilizar.
4. Se descargan los datos desde el INE.
5. Se selecciona automáticamente el último periodo completo.
6. Se genera el archivo Excel.
7. Se incorpora la nota de prensa.
8. Se obtiene la próxima fecha de publicación.
9. Se genera y envía el email.
10. El agente finaliza el proceso.

---

## Guardrails implementados

- Límite máximo de llamadas a APIs.
- Uso exclusivo de datos oficiales del INE.
- Prohibición de inventar datos.
- Restricción de destinatarios autorizados.
- No realiza recomendaciones económicas ni financieras.
- Control del número máximo de pasos del agente.

---

## Posibles mejoras futuras

- Automatizar la localización de la nota de prensa.
- Programar ejecuciones periódicas automáticas.
- Incorporar nuevos indicadores del INE.
- Generar informes PDF automáticos.
- Desplegar el agente en la nube.

---

## Fuente de datos

Instituto Nacional de Estadística (INE):

https://www.ine.es/

API oficial:

https://www.ine.es/dyngs/DAB/index.htm?cid=1099
