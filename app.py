import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de página
st.set_page_config(page_title="CropPlanner Pro", layout="wide")

st.title("🌾 CropPlanner: Modelo de Análisis y Proyección de Rendimiento")

@st.cache_data
def load_data():
    df = pd.read_excel('Analisis final.xlsx')
    # Extraer Tabla 6 (datos base)
    df_base = df.iloc[1:, 1:14].copy()
    df_base.columns = ['Finca', 'Lote', 'Area', 'Ciclo', 'Codigo', 'Vegetal', 'Referencia', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio', 'Mes']
    
    # Limpieza
    for col in ['Area', 'Ciclo', 'Codigo', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio']:
        df_base[col] = pd.to_numeric(df_base[col], errors='coerce')
    
    df_base['Periodo'] = df_base['Anio'].apply(lambda x: 'Actual (2025-2026)' if x >= 2025 else 'Historico (<2025)')
    
    # Lógica de curva real
    df_base = df_base.sort_values(['Vegetal', 'Finca', 'Lote', 'Ciclo', 'Codigo'])
    df_base['Semana_Rel'] = df_base.groupby(['Vegetal', 'Finca', 'Lote', 'Ciclo']).cumcount() + 1
    df_base['Total_Ciclo'] = df_base.groupby(['Vegetal', 'Finca', 'Lote', 'Ciclo'])['Kilos'].transform('sum')
    df_base['Pct_Semanal'] = (df_base['Kilos'] / df_base['Total_Ciclo']) * 100
    return df_base

df_data = load_data()

# Sidebar: Filtros
st.sidebar.header("Filtros de Análisis")
vegetales_disponibles = sorted(df_data['Vegetal'].dropna().unique())
sel_vegetales = st.sidebar.multiselect("Seleccionar Vegetales:", vegetales_disponibles, default=vegetales_disponibles[:1])

# Filtrado de datos
df_filtered = df_data[df_data['Vegetal'].isin(sel_vegetales)]

# Pestañas de Análisis
tab1, tab2 = st.tabs(["📊 Matriz de Curvas (Real)", "📈 Análisis de Proyección"])

with tab1:
    st.subheader("Distribución Porcentual Real (%) por Semana")
    
    # Pivotar matriz
    matriz = df_filtered.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().unstack(fill_value=0)
    
    # Formatear tabla
    st.dataframe(matriz.style.format("{:.2f}%"), use_container_width=True)
    
    st.markdown("---")
    st.subheader("Gráfica Comparativa: Curva Histórica vs Actual")
    
    # Reestructurar para graficar
    df_plot = df_filtered.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().reset_index()
    fig = px.line(df_plot, x='Semana_Rel', y='Pct_Semanal', color='Periodo', 
                  facet_col='Vegetal', markers=True, 
                  labels={'Semana_Rel': 'Semana de Cosecha', 'Pct_Semanal': 'Distribución (%)'},
                  title="Evolución de la Curva de Producción")
    st.plotly_chart(fig, use_container_width=True)

with tab2:
    st.header("Modelo de Proyección")
    st.write("Aquí puedes implementar tu lógica de rendimiento (Kilos/Hectárea).")
    
    # Ejemplo de cálculo de rendimiento real
    rendimiento = df_filtered.groupby(['Vegetal', 'Periodo'])['Kilos'].sum().reset_index()
    st.table(rendimiento)
    st.info("Para las futuras planificaciones, utiliza la 'Curva Actual' proyectando los Kilos/Hectárea esperados multiplicados por el % de la curva.")
