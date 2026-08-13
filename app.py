import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Configuración de la Aplicación
st.set_page_config(
    page_title="CropPlanner - Análisis de Ciclos y Curvas",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌾 CropPlanner: Análisis Detallado del Ciclo por Vegetal")
st.markdown("Comparativa exacta del comportamiento real semana a semana (Histórico vs Actual).")

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
    df_t6 = df_raw.iloc[1:, 1:14].copy()
    df_t6.columns = ["Finca", "Lote", "Area", "Ciclo", "Codigo", "Vegetal", "Referencia", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio", "Mes"]
    
    for col in ["Area", "Ciclo", "Codigo", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio"]:
        df_t6[col] = pd.to_numeric(df_t6[col], errors="coerce")
    
    df_t6 = df_t6.dropna(subset=["Vegetal", "Ciclo", "Kilos"])
    df_t6["Periodo"] = df_t6["Anio"].apply(lambda x: "Actual (2025-2026)" if x >= 2025 else "Histórico (<2025)")
    return df_t6

df_base = cargar_datos()

# Incorporar nuevos registros si existen
if os.path.exists(ARCHIVO_NUEVOS_DATOS):
    df_nuevos = pd.read_csv(ARCHIVO_NUEVOS_DATOS)
    if not df_nuevos.empty:
        df_base = pd.concat([df_base, df_nuevos], ignore_index=True)

if df_base.empty:
    st.error("❌ No se encontraron datos para procesar en el archivo maestro.")
    st.stop()

# 3. Interfaz de Pestañas
tab1, tab2, tab3 = st.tabs(["📊 Matriz de Comportamiento Real", "📈 Curvas Dinámicas", "🚀 Planificador"])

with tab1:
    st.header("📊 Comportamiento Real de Cosecha por Semana (Ciclo por Ciclo)")
    st.markdown("""
    Esta matriz analiza **cada ciclo de manera independiente** para calcular qué porcentaje real de la cosecha 
    se obtiene en la Semana 1, Semana 2, Semana 3, etc., agrupado por **Vegetal** y separado por **Periodo**.
    """)

    # Cálculo de la semana relativa dentro de cada ciclo individual
    df_v = df_base.copy()
    df_v = df_v.sort_values(["Vegetal", "Finca", "Lote", "Ciclo", "Anio", "Semana"])
    df_v["Sem_Rel"] = df_v.groupby(["Vegetal", "Finca", "Lote", "Ciclo"]).cumcount() + 1
    
    # Normalizar: calcular el porcentaje de cada semana respecto al total de su propio ciclo
    tot_ciclo = df_v.groupby(["Vegetal", "Finca", "Lote", "Ciclo"])["Kilos"].transform("sum")
    df_v["Pct"] = (df_v["Kilos"] / tot_ciclo) * 100
    
    # Agrupar el promedio por Vegetal, Periodo y Semana Relativa
    matriz_base = df_v.groupby(["Vegetal", "Periodo", "Sem_Rel"])["Pct"].mean().reset_index()
    
    # Pivotar para que las semanas sean columnas (Semana 1, Semana 2...)
    pivot_matriz = matriz_base.pivot(index=["Vegetal", "Periodo"], columns="Sem_Rel", values="Pct").fillna(0)
    
    # Limitar o asegurar hasta un número razonable de columnas de semanas (ej. hasta la semana 10 o max disponible)
    # Renombrar columnas a formato "Semana X"
    pivot_matriz.columns = [f"Semana {c}" for c in pivot_matriz.columns]
    
    # Calcular la columna de Total % para verificar que sumen ~100%
    pivot_matriz["Total %"] = pivot_matriz.sum(axis=1)
    
    # Formatear todos los valores a porcentaje con 2 decimales
    pivot_display = pivot_matriz.reset_index()
    for col in pivot_display.columns:
        if col not in ["Vegetal", "Periodo"]:
            pivot_display[col] = pivot_display[col].apply(lambda x: f"{x:.2f}%")

    # Mostrar la tabla completa estilo matriz
    st.dataframe(pivot_display, use_container_width=True, hide_index=True)

    # Gráfica global o por selección al final
    st.markdown("---")
    st.subheader("📈 Gráfica de Tendencia por Vegetal")
    veg_grafica = st.selectbox("Seleccione Vegetal para visualizar su curva:", sorted(df_base["Vegetal"].dropna().unique()))
    
    df_graf = matriz_base[matriz_base["Vegetal"] == veg_grafica]
    fig_c = px.line(
        df_graf, 
        x="Sem_Rel", 
        y="Pct", 
        color="Periodo", 
        markers=True, 
        labels={"Sem_Rel": "Semana de Cosecha", "Pct": "Porcentaje del Total (%)"},
        title=f"Evolución real del ciclo: {veg_grafica}"
    )
    st.plotly_chart(fig_c, use_container_width=True)

with tab2:
    st.header("📈 Curvas Dinámicas")
    st.write("Análisis general de rendimiento por hectárea.")

with tab3:
    st.header("🚀 Planificador de Siembras")
    st.info("Módulo de pronóstico de cosechas futuras.")
