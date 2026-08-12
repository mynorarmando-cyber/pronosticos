import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from agronomic_forecast_engine_3 import AgronomicForecastEngine

st.set_page_config(
    page_title="CropPlanner - Motor de Pronóstico Agrícola",
    page_layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌾 CropPlanner: Sistema de Proyección de Harvest Curves")
st.markdown("Plataforma interactiva para estimación de cosechas con **ponderación temporal** e **índices de estacionalidad**.")

@st.cache_resource
def load_engine():
    return AgronomicForecastEngine('Analisis final.xlsx')

try:
    engine = load_engine()
    st.sidebar.success("Base de datos cargada correctamente")
except Exception as e:
    st.error(f"Error al cargar la base de datos: {e}")
    st.stop()

# Controles laterales
st.sidebar.header("📋 Parámetros de la Nueva Siembra")

vegetales_disponibles = sorted(engine.rendimientos_base['Referencia'].dropna().unique())
vegetal_sel = st.sidebar.selectbox("Seleccionar Vegetal / Cultivo:", vegetales_disponibles)

area_ha = st.sidebar.number_input("Área a Sembrar (Hectáreas):", min_value=0.1, max_value=500.0, value=5.0, step=0.5)
fecha_siembra = st.sidebar.date_input("Fecha de Siembra:", value=pd.to_datetime('2026-09-01'))

if st.sidebar.button("🚀 Generar Pronóstico"):
    totales, detalle = engine.generar_pronostico(
        vegetal=vegetal_sel, 
        area_ha=area_ha, 
        fecha_siembra_str=fecha_siembra.strftime("%Y-%m-%d")
    )

    if totales is None:
        st.error("No hay registros suficientes para proyectar este cultivo.")
    else:
        # Indicadores clave
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("📦 Escenario Probable (P50)", f"{totales['Total_Probable_Kg']:,.1f} Kg")
        col2.metric("🛡️ Escenario Conservador (P25)", f"{totales['Total_Conservador_Kg']:,.1f} Kg")
        col3.metric("📈 Escenario Optimista (P75)", f"{totales['Total_Optimista_Kg']:,.1f} Kg")
        col4.metric("⏱️ Duración Cosecha", f"{totales['Duracion_Semanas']} semanas")

        st.markdown("---")

        # Gráfico comparativo
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=detalle['Semana_Calendario'],
            y=detalle['Kilos_Conservador'],
            name='Conservador (P25)',
            marker_color='#FF8C00'
        ))
        fig.add_trace(go.Bar(
            x=detalle['Semana_Calendario'],
            y=detalle['Kilos_Probable'],
            name='Probable (P50)',
            marker_color='#2E8B57'
        ))
        fig.add_trace(go.Bar(
            x=detalle['Semana_Calendario'],
            y=detalle['Kilos_Optimista'],
            name='Optimista (P75)',
            marker_color='#4682B4'
        ))

        fig.update_layout(
            title=f"Proyección Semanal de Cosecha - {vegetal_sel} ({area_ha} Ha)",
            xaxis_title="Semana Calendario del Año",
            yaxis_title="Producción Estimada (Kg)",
            barmode='group',
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)

        # Detalle tabular
        st.subheader("📅 Detalle Semanal de Producción")
        st.dataframe(
            detalle[['Semana_Relativa', 'Semana_Calendario', 'Pct_Curva', 'Factor_Estacional', 'Kilos_Conservador', 'Kilos_Probable', 'Kilos_Optimista']],
            use_container_width=True
        )
