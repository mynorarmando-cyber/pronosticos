import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Configuración de la Aplicación
st.set_page_config(
    page_title="CropPlanner - Análisis de Ciclos",
    layout="wide",
)

st.title("🌾 CropPlanner: Análisis de Ciclos y Comportamiento Real")

# Rutas
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_MAESTRO = os.path.join(BASE_DIR, "Analisis final.xlsx")
ARCHIVO_NUEVOS_DATOS = os.path.join(BASE_DIR, "registros_nuevos_cosecha.csv")

# 2. Carga y Procesamiento de Datos
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

# 3. Interfaz con las Pestañas
tab1, tab2, tab3 = st.tabs(["📊 Diagnóstico de Ciclos", "📈 Curvas Dinámicas", "🚀 Planificador"])

with tab1:
    st.header("📊 Diagnóstico y Comportamiento Real del Ciclo")
    veg_sel = st.selectbox("Seleccione Vegetal para análisis de ciclo:", sorted(df_base["Vegetal"].dropna().unique()))
    
    # A. Resumen General
    st.subheader("1. Resumen Estadístico por Periodo")
    resumen = df_base[df_base["Vegetal"] == veg_sel].groupby("Periodo").agg({
        "Dur_SC": "mean", 
        "Rendimiento_Semanal": "sum"
    }).reset_index()
    st.dataframe(resumen, use_container_width=True)

    # B. Comportamiento Real por Semana (La curva de vida del cultivo)
    st.subheader("2. Comportamiento Real del Ciclo (%)")
    
    # Calcular semana relativa y porcentaje por semana
    df_v = df_base[df_base["Vegetal"] == veg_sel].copy()
    df_v = df_v.sort_values(["Finca", "Lote", "Ciclo", "Anio", "Semana"])
    df_v["Sem_Rel"] = df_v.groupby(["Finca", "Lote", "Ciclo"]).cumcount() + 1
    
    tot_ciclo = df_v.groupby(["Finca", "Lote", "Ciclo"])["Kilos"].transform("sum")
    df_v["Pct"] = (df_v["Kilos"] / tot_ciclo) * 100
    
    # Agrupar promedio por Periodo y Semana Relativa
    curva_real = df_v.groupby(["Periodo", "Sem_Rel"])["Pct"].mean().reset_index()
    
    # Tabla pivote: Periodo (fila) vs Semana X (columna)
    pivot_tabla = curva_real.pivot(index="Periodo", columns="Sem_Rel", values="Pct").fillna(0)
    pivot_tabla.columns = [f"Semana {c} (%)" for c in pivot_tabla.columns]
    
    # Mostrar tabla detallada
    st.dataframe(pivot_tabla.reset_index(), use_container_width=True, hide_index=True)

    # C. Gráfica Comparativa (Siempre al final de la pestaña)
    st.markdown("---")
    st.subheader("3. Gráfica Comparativa de Curvas")
    fig_c = px.line(
        curva_real, 
        x="Sem_Rel", 
        y="Pct", 
        color="Periodo", 
        markers=True, 
        labels={"Sem_Rel": "Semana de vida del cultivo", "Pct": "% de cosecha total"},
        title=f"Evolución del ciclo de cosecha: Actual vs Histórico"
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab2:
    st.header("📈 Curvas Dinámicas")
    st.write("Análisis adicional de rendimiento.")

with tab3:
    st.header("🚀 Planificador")
    st.info("Módulo de pronóstico basado en los datos anteriores.")
