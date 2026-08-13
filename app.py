import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de la aplicación
st.set_page_config(page_title="CropPlanner Pro", layout="wide")
st.title("🌾 CropPlanner: Modelo de Análisis y Proyección de Cosechas")

@st.cache_data
def load_and_clean_data():
    df = pd.read_excel('Analisis final.xlsx')
    df_base = df.iloc[1:, 1:14].copy()
    df_base.columns = ['Finca', 'Lote', 'Area', 'Ciclo', 'Codigo', 'Vegetal', 'Referencia', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio', 'Mes']
    
    # Conversión de tipos numéricos
    for col in ['Area', 'Ciclo', 'Codigo', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio']:
        df_base[col] = pd.to_numeric(df_base[col], errors='coerce')
    
    df_base['Periodo'] = df_base['Anio'].apply(lambda x: 'Actual (2025-2026)' if x >= 2025 else 'Historico (<2025)')
    
    # 1. Calcular la duración real (número de semanas de cosecha) por cada ciclo único
    dur_ciclo = df_base.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo'], as_index=False)['Semana'].nunique()
    dur_ciclo.rename(columns={'Semana': 'Duracion_Real'}, inplace=True)
    
    # 2. Filtrar outliers (casos raros/extremos) usando el rango intercuartil (IQR) de forma segura
    valid_cycles = []
    for (veg, per), group in dur_ciclo.groupby(['Vegetal', 'Periodo']):
        q1 = group['Duracion_Real'].quantile(0.25)
        q3 = group['Duracion_Real'].quantile(0.75)
        iqr = q3 - q1
        limite_superior = q3 + 1.5 * iqr
        # Si IQR es 0, permitimos todos o al menos el límite mínimo
        if iqr == 0:
            limite_superior = group['Duracion_Real'].max()
            
        filtered_group = group[group['Duracion_Real'] <= limite_superior]
        valid_cycles.append(filtered_group)
        
    ciclos_limpios = pd.concat(valid_cycles, ignore_index=True)
    
    # 3. Filtrar el dataframe base manteniendo únicamente los ciclos normales (sin extremos)
    df_limpio = df_base.merge(
        ciclos_limpios[['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']], 
        on=['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']
    )
    
    # 4. Calcular la semana relativa y el porcentaje de aporte de cada semana al total de su ciclo
    df_limpio = df_limpio.sort_values(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo', 'Codigo'])
    df_limpio['Semana_Rel'] = df_limpio.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']).cumcount() + 1
    tot_ciclo = df_limpio.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo'])['Kilos'].transform('sum')
    df_limpio['Pct_Semanal'] = (df_limpio['Kilos'] / tot_ciclo) * 100
    
    return df_limpio

df_data = load_and_clean_data()

# Interfaz de Usuario
st.sidebar.header("Panel de Control")
vegetales = sorted(df_data['Vegetal'].dropna().unique())
sel_veg = st.sidebar.multiselect("Seleccionar Vegetales:", vegetales, default=vegetales[:1])

df_filt = df_data[df_data['Vegetal'].isin(sel_veg)]

# Secciones en pestañas
tab1, tab2 = st.tabs(["📊 Matriz de Curvas (Limpia)", "📈 Proyección y Tendencias"])

with tab1:
    st.subheader("Matriz de Comportamiento Porcentual Real por Semana")
    st.markdown("Los datos extremos o eventuales (como ciclos con duración atípica) han sido filtrados estadísticamente.")
    
    if not df_filt.empty:
        matriz = df_filt.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().unstack(fill_value=0)
        st.dataframe(matriz.style.format("{:.2f}%"), use_container_width=True)
    else:
        st.warning("Seleccione al menos un vegetal en la barra lateral.")

with tab2:
    st.subheader("Gráfica Comparativa de Curvas de Producción")
    if not df_filt.empty:
        df_plot = df_filt.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().reset_index()
        fig = px.line(
            df_plot, 
            x='Semana_Rel', 
            y='Pct_Semanal', 
            color='Periodo', 
            facet_col='Vegetal', 
            facet_col_wrap=2,
            markers=True,
            labels={'Semana_Rel': 'Semana Relativa de Cosecha', 'Pct_Semanal': 'Porcentaje del Ciclo (%)'},
            title="Evolución Normalizada del Ciclo de Cosecha"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Seleccione al menos un vegetal.")
