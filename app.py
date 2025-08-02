# app.py
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURACIÓN INICIAL ---
APP_TITLE = "Análisis de Evoluciones de Fisioterapia"
st.set_page_config(page_title=APP_TITLE, layout="wide")

ATTRIBUTE_GROUPS = {
    "Cualidades Físicas": [
        'Realiza levantamiento de pelota de 1.5 kg', 'Realiza levantamiento de pelota de 2.0 kg',
        'Realiza levantamiento de pelota de 3.0 kg', 'Realiza levantamiento de mas de 3.0 kg',
        'Levanta y mantiene por 10 segundos.', 'Levanta y mantiene por mas de 10 segundos',
        'Levanta, mantiene y se desplaza.'
    ],
    "Coordinación": [
        'Presenta adecuada coordinacion visomanual.', 'Presenta adecuada coordinacion visopedica.'
    ],
    "Equilibrio": [
        'Realiza traslado sobre barra de equilibrio.', 'Se sostiene en balancin en un solo pie.',
        'Se sostiene en balancin con 2 pies por 10 segundos.',
        'Se sostiene en balancin con 2 pies por 20 segundos.',
        'Se sostiene en balancin con 2 pies por 30 segundos.'
    ],
    "PATRONES FUNDAMENTALES DE MOVIMIENTO": {
        "PATRONES LOCOMOTORES": [
            'Salto en dos pies.', 'Salto en un pie.', 'Realiza arrastre.', 'Realiza rollos.',
            'Realiza rolados.', 'Realiza carrera.', 'Trepa.'
        ],
        "PATRONES MANIPULATIVOS": [
            'Lanza pelota con ambas manos.', 'Lanza pelota con la mano derecha.',
            'Lanza pelota con la mano izquierda.', 'Atrapa pelotas.', 'Empuja.', 'Patea.',
            'Hala.', 'Alcanza.', 'Levanta desde el piso.'
        ],
        "PLANEAMIENTO MOTOR": [
            'Planea, inicia y ejecuta actividades motoras.',
            'Busca estrategias para dar solucion a problemas motores.'
        ]
    }
}

# --- LÓGICA DEL BACKEND ---
@st.cache_data(ttl="10m")
def load_data():
    """Carga los datos desde Google Sheets usando las credenciales de Streamlit Secrets."""
    try:
        # --- LA LÍNEA QUE CAMBIÓ ESTÁ AQUÍ ---
        # Añadimos el permiso de Google Drive para que la app pueda buscar el archivo por su nombre.
        scopes = [
            'https://www.googleapis.com/auth/spreadsheets',
            'https://www.googleapis.com/auth/drive'
        ]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scopes)
        gc = gspread.authorize(creds)

        # Abre la hoja de cálculo por su nombre y la pestaña por su nombre
        spreadsheet = gc.open("Resultados de Fisioterapia")
        worksheet = spreadsheet.worksheet("Resultados")

        # Carga los datos a un DataFrame de Pandas
        df = pd.DataFrame(worksheet.get_all_records())

        # Limpieza de datos
        df['ID'] = df['ID'].astype(str).str.replace(r'\.0$', '', regex=True)
        return df
    except Exception as e:
        st.error(f"Error al cargar los datos: {e}")
        st.error("Verifica que los 'Secrets' en Streamlit estén bien configurados y que la hoja de Google fue compartida con el email del servicio.")
        return pd.DataFrame()

def calculate_result(val1, val2):
    """Calcula la diferencia entre dos valores, manejando el caso 'NA'."""
    try:
        num1 = float(val1)
        num2 = float(val2)
        return round(num1 - num2, 2)
    except (ValueError, TypeError):
        return 'NA'

# --- INTERFAZ DE USUARIO (UI) ---
st.title(APP_TITLE)
st.write("Herramienta para visualizar y comparar la evolución de un paciente entre dos fechas.")

df = load_data()

if not df.empty:
    df['Paciente Busqueda'] = df['Nombre'] + ' - ID: ' + df['ID']
    patient_list = [''] + sorted(df['Paciente Busqueda'].unique().tolist())

    st.header("1. Seleccione el Paciente")
    selected_patient = st.selectbox(
        "Buscar por nombre o número de identificación",
        options=patient_list, index=0, placeholder="Escriba para buscar..."
    )

    if selected_patient:
        patient_df = df[df['Paciente Busqueda'] == selected_patient].copy()
        available_dates = sorted(patient_df['Fecha Evolución'].unique(), reverse=True)

        st.header("2. Seleccione las Fechas a Comparar")
        if len(available_dates) < 2:
            st.warning("Este paciente solo tiene un registro. Se necesita al menos dos evoluciones para poder comparar.")
        else:
            col1, col2 = st.columns(2)
            with col1:
                date1 = st.selectbox("Fecha de inicio del análisis", options=available_dates, help="Evolución Reciente")

            date2_options = [d for d in available_dates if d != date1]
            with col2:
                date2 = st.selectbox("Fecha de fin del análisis", options=date2_options, help="Fecha de comparación")

            if st.button("Correr Análisis Comparativo", type="primary"):
                if date1 and date2:
                    st.header(f"Resultados para: {selected_patient}")
                    row1 = patient_df[patient_df['Fecha Evolución'] == date1].iloc[0]
                    row2 = patient_df[patient_df['Fecha Evolución'] == date2].iloc[0]

                    for group_name, items in ATTRIBUTE_GROUPS.items():
                        st.subheader(group_name)
                        # Grupo simple
                        if isinstance(items, list):
                            table_data = []
                            for attr in items:
                                val1, val2 = row1.get(attr, 'NA'), row2.get(attr, 'NA')
                                table_data.append({
                                    'Atributo': attr, 'Fecha Evolutiva': val1,
                                    'Fecha Comparativa': val2, 'Resultado': calculate_result(val1, val2)
                                })
                            st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
                        # Grupo con subgrupos
                        else: 
                            for subgroup_name, sub_items in items.items():
                                st.markdown(f"**{subgroup_name}**")
                                table_data = []
                                for attr in sub_items:
                                    val1, val2 = row1.get(attr, 'NA'), row2.get(attr, 'NA')
                                    table_data.append({
                                        'Atributo': attr, 'Fecha Evolutiva': val1,
                                        'Fecha Comparativa': val2, 'Resultado': calculate_result(val1, val2)
                                    })
                                st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)
                else:
                    st.error("Por favor, seleccione ambas fechas para realizar el análisis.")
