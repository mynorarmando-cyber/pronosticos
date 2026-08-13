import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración
st.set_page_config(page_title="CropPlanner Pro - Análisis Limpio", layout="wide")
st.title("🌾 CropPlanner: Modelo de Análisis con Filtro de Outliers")

@st.cache_data
def load_and_clean_data():
    df = pd.read_excel('Analisis final.xlsx')
    df_base = df.iloc[1:, 1:14].copy()
    df_base.columns = ['Finca', 'Lote', 'Area', 'Ciclo', 'Codigo', 'Vegetal', 'Referencia', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio', 'Mes']
    
    # Conversión
    for col in ['Area', 'Ciclo', 'Codigo', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio']:
        df_base[col] = pd.to_numeric(df_base[col], errors='coerce')
    
    df_base['Periodo'] = df_base['Anio'].apply(lambda x: 'Actual (2025-2026)' if x >= 2025 else 'Historico (<2025)')
    
    # 1. Identificar duración real por ciclo
    dur_ciclo = df_base.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo'])['Semana'].nunique().reset_index()
    dur_ciclo.rename(columns={'Semana': 'Duracion_Real'}, inplace=True)
    
    # 2. Filtrar Outliers (IQR) por Vegetal y Periodo
    def filtrar_iqr(g):
        q1, q3 = g['Duracion_Real'].quantile([0.25, 0.75])
        limite = q3 + 1.5 * (q3 - q1) # Límite superior robusto
        return g[g['Duracion_Real'] <= limite]
    
    ciclos_limpios = dur_ciclo.groupby(['Vegetal', 'Periodo'], group_keys=False).apply(filtrar_iqr)
    
    # 3. Mezclar con el DF base para filtrar el origen
    df_limpio = df_base.merge(ciclos_limpios[['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']], on=['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo'])
    
    # 4. Calcular curvas relativas sobre los datos limpios
    df_limpio = df_limpio.sort_values(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo', 'Codigo'])
    df_limpio['Semana_Rel'] = df_limpio.groupby(['Vegetal', 'Finca', 'Lote', 'Ciclo']).cumcount() + 1
    tot = df_limpio.groupby(['Vegetal', 'Finca', 'Lote', 'Ciclo'])['Kilos'].transform('sum')
    df_limpio['Pct_Semanal'] = (df_limpio['Kilos'] / tot) * 100
    
    return df_limpio

df_data = load_and_clean_data()

# Interfaz
vegetales = sorted(df_data['Vegetal'].dropna().unique())
sel_veg = st.multiselect("Filtrar Vegetales:", vegetales, default=vegetales[:1])
df_filt = df_data[df_data['Vegetal'].isin(sel_veg)]

# Tabla de Resultados
st.subheader("Curva de Producción Limpia (%)")
matriz = df_filt.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().unstack(fill_value=0)
st.dataframe(matriz.style.format("{:.2f}%"), use_container_width=True)

# Visualización
st.subheader("Gráfica de Tendencia (Proyección)")
fig = px.line(df_filt.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().reset_index(), 
              x='Semana_Rel', y='Pct_Semanal', color='Periodo', facet_col='Vegetal', markers=True)
st.plotly_chart(fig, use_container_width=True)
