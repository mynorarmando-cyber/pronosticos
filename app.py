import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Configuración de la Aplicación
st.set_page_config(
    page_title="CropPlanner - Análisis Agrícola",
    layout="wide",
)

st.title("🌾 CropPlanner: Análisis y Pronósticos")

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_MAESTRO = os.path.join(BASE_DIR, "Analisis final.xlsx")
ARCHIVO_NUEVOS_DATOS = os.path.join(BASE_DIR, "registros_nuevos_cosecha.csv")

# 2. Carga de Datos
@st.cache_data
def cargar_datos():
    if not os.path.exists(ARCHIVO_MAESTRO):
        return pd.DataFrame()
    df_raw = pd.read_excel(ARCHIVO_MAESTRO, sheet_name="Hoja1")
    df_t6 = df_raw.iloc[1:, 1:14].copy()
    df_t6.columns = ["Finca", "Lote", "Area", "Ciclo", "Codigo", "Vegetal", "Referencia", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio", "Mes"]
    
    for col in ["Area", "Ciclo", "Codigo", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio"]:
        df_t6[col] = pd.to_numeric(df_t6[col], errors="coerce")
    
    df_t6 = df_t6.dropna(subset=["Vegetal", "Ciclo", "Kilos"])
    df_t6["Periodo"] = df_t6["Anio"].apply(lambda x: "Actual (2025-2026)" if x >= 2025 else "Histórico (<2025)")
    df_t6["Area_Efectiva"] = np.where(df_t6["Cantidad_V"] > 1, df_t6["Area"] / df_t6["Cantidad_V"], df_t6["Area"])
    df_t6["Rendimiento_Semanal"] = df_t6["Kilos"] / df_t6["Area_Efectiva"]
    return df_t6

df_base = cargar_datos()

# 3. Estructura de la Interfaz
tab1, tab2, tab3 = st.tabs(["📊 Diagnóstico", "📈 Curvas Dinámicas", "🚀 Planificador"])

with tab1:
    st.header("📊 Comportamiento de Duración")
    veg_sel = st.selectbox("Seleccione Vegetal:", sorted(df_base["Vegetal"].dropna().unique()))
    
    # Resumen Duración
    resumen = df_base[df_base["Vegetal"] == veg_sel].groupby("Periodo").agg({"Dur_SC": "mean", "Rendimiento_Semanal": "sum"}).reset_index()
    st.dataframe(resumen, use_container_width=True)

    st.subheader("📅 Distribución Semanal (%)")
    
    # Preparar datos de curvas
    df_v = df_base[df_base["Vegetal"] == veg_sel].copy()
    df_v = df_v.sort_values(["Finca", "Lote", "Ciclo", "Anio", "Semana"])
    df_v["Sem_Rel"] = df_v.groupby(["Finca", "Lote", "Ciclo"]).cumcount() + 1
    
    tot_ciclo = df_v.groupby(["Finca", "Lote", "Ciclo"])["Kilos"].transform("sum")
    df_v["Pct"] = (df_v["Kilos"] / tot_ciclo) * 100
    
    curva_plot = df_v.groupby(["Periodo", "Sem_Rel"])["Pct"].mean().reset_index()
    
    # Tabla pivote: Periodo como primera columna, semanas después
    pivot_curva = curva_plot.pivot(index="Periodo", columns="Sem_Rel", values="Pct").fillna(0)
    pivot_curva.columns = [f"Semana {c} (%)" for c in pivot_curva.columns]
    
    # Mostrar tabla (Reset index para que 'Periodo' sea columna)
    st.dataframe(pivot_curva.reset_index(), use_container_width=True, hide_index=True)

    # Gráfica al final
    st.markdown("---")
    fig_c = px.line(
        curva_plot, 
        x="Sem_Rel", 
        y="Pct", 
        color="Periodo", 
        markers=True, 
        title=f"Gráfica de Distribución Semanal - {veg_sel}"
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab2:
    st.header("📈 Comparativa General")
    st.write("Utilice esta pestaña para análisis comparativos rápidos entre diferentes vegetales.")

with tab3:
    st.header("🚀 Planificador")
    st.info("Módulo de pronóstico en construcción.")
