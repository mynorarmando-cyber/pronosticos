import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Configuración de la Aplicación
st.set_page_config(
    page_title="CropPlanner - Análisis Profesional de Cosechas",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌾 CropPlanner: Sistema de Análisis de Cosechas")
st.markdown("Comparativa de comportamiento real entre periodos Históricos y Actuales.")

# Rutas de archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_MAESTRO = os.path.join(BASE_DIR, "Analisis final.xlsx")
ARCHIVO_NUEVOS_DATOS = os.path.join(BASE_DIR, "registros_nuevos_cosecha.csv")

# 2. Carga y Procesamiento de Datos
@st.cache_data
def cargar_datos():
    if not os.path.exists(ARCHIVO_MAESTRO):
        return pd.DataFrame()
    
    df_raw = pd.read_excel(ARCHIVO_MAESTRO, sheet_name="Hoja1")
    # Ajuste de columnas basado en estructura del archivo maestro
    df_t6 = df_raw.iloc[1:, 1:14].copy()
    df_t6.columns = ["Finca", "Lote", "Area", "Ciclo", "Codigo", "Vegetal", "Referencia", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio", "Mes"]
    
    for col in ["Area", "Ciclo", "Codigo", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio"]:
        df_t6[col] = pd.to_numeric(df_t6[col], errors="coerce")
    
    df_t6 = df_t6.dropna(subset=["Vegetal", "Ciclo", "Kilos"])
    df_t6["Periodo"] = df_t6["Anio"].apply(lambda x: "Actual (2025-2026)" if x >= 2025 else "Histórico (<2025)")
    return df_t6

df_base = cargar_datos()

# 3. Interfaz Principal
tab1, tab2, tab3 = st.tabs(["📊 Diagnóstico y Tabla Comparativa", "📈 Curvas Dinámicas", "🚀 Planificador"])

with tab1:
    st.header("📊 Comparativa de Comportamiento Real: Histórico vs Actual")
    veg_sel = st.selectbox("Seleccione el Vegetal a comparar:", sorted(df_base["Vegetal"].dropna().unique()))
    
    # A. Resumen General
    st.subheader("1. Resumen de Ciclos")
    resumen = df_base[df_base["Vegetal"] == veg_sel].groupby("Periodo").agg({
        "Dur_SC": "mean", 
        "Kilos": "sum"
    }).reset_index().rename(columns={"Dur_SC": "Duración Prom. (Sem)", "Kilos": "Total Kilos"})
    st.dataframe(resumen, use_container_width=True, hide_index=True)

    # B. Tabla Detallada por Semana (El corazón de la comparativa)
    st.subheader(f"2. Distribución Semanal Real (%) - {veg_sel}")
    
    # Lógica de cálculo de semana relativa
    df_v = df_base[df_base["Vegetal"] == veg_sel].copy()
    df_v = df_v.sort_values(["Finca", "Lote", "Ciclo", "Anio", "Semana"])
    df_v["Sem_Rel"] = df_v.groupby(["Finca", "Lote", "Ciclo"]).cumcount() + 1
    
    # Calcular el porcentaje que aporta cada semana al total de su ciclo
    tot_ciclo = df_v.groupby(["Finca", "Lote", "Ciclo"])["Kilos"].transform("sum")
    df_v["Pct"] = (df_v["Kilos"] / tot_ciclo) * 100
    
    # Agrupación para comparar periodos
    curva_real = df_v.groupby(["Periodo", "Sem_Rel"])["Pct"].mean().reset_index()
    
    # Pivoteo para formato matricial (como Excel)
    pivot_tabla = curva_real.pivot(index="Periodo", columns="Sem_Rel", values="Pct").fillna(0)
    pivot_tabla.columns = [f"Semana {c}" for c in pivot_tabla.columns]
    
    # Agregar columna de Total %
    pivot_tabla["Total %"] = pivot_tabla.sum(axis=1)
    
    # Formateo visual a porcentaje
    pivot_display = pivot_tabla.reset_index()
    for col in pivot_display.columns:
        if col not in ["Periodo"]:
            pivot_display[col] = pivot_display[col].apply(lambda x: f"{x:.2f}%")
            
    st.dataframe(pivot_display, use_container_width=True, hide_index=True)

    # C. Gráfica Comparativa (Final de la pestaña)
    st.markdown("---")
    st.subheader("3. Gráfica de Tendencia")
    fig_c = px.line(
        curva_real, 
        x="Sem_Rel", 
        y="Pct", 
        color="Periodo", 
        markers=True, 
        labels={"Sem_Rel": "Semana de Cosecha", "Pct": "Distribución (%)"},
        title=f"Curva de producción: {veg_sel}"
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab2:
    st.header("📈 Análisis de Rendimiento")
    st.write("Análisis detallado de productividad por lote y finca.")

with tab3:
    st.header("🚀 Planificador de Siembras")
    st.info("Utilice los datos de comportamiento real de la pestaña 1 para proyectar próximas cosechas.")
