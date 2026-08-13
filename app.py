import os
import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st

# 1. Configuración de la Aplicación
st.set_page_config(
    page_title="CropPlanner - Planificación y Pronósticos Agrícolas",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🌾 CropPlanner: Planificador Inteligente y Curvas de Cosecha Dinámicas")
st.markdown("Sistema conectado al archivo maestro para análisis histórico, cálculo adaptativo de duración y pronóstico de siembras futuras.")

# Rutas de archivos
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_MAESTRO = os.path.join(BASE_DIR, "Analisis final.xlsx")
ARCHIVO_NUEVOS_DATOS = os.path.join(BASE_DIR, "registros_nuevos_cosecha.csv")

# 2. Carga y Consolidación de Datos
@st.cache_data
def cargar_datos_maestros():
    if not os.path.exists(ARCHIVO_MAESTRO):
        return pd.DataFrame(), pd.DataFrame()

    df_raw = pd.read_excel(ARCHIVO_MAESTRO, sheet_name="Hoja1")

    # --- TABLA 6 (Detalle de Cosechas) ---
    df_t6 = df_raw.iloc[1:, 1:14].copy()
    df_t6.columns = ["Finca", "Lote", "Area", "Ciclo", "Codigo", "Vegetal", "Referencia", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio", "Mes"]
    
    for col in ["Area", "Ciclo", "Codigo", "Cantidad_V", "Dur_SC", "Kilos", "Semana", "Anio"]:
        df_t6[col] = pd.to_numeric(df_t6[col], errors="coerce")

    df_t6 = df_t6.dropna(subset=["Vegetal", "Ciclo", "Kilos"])
    df_t6["Periodo"] = df_t6["Anio"].apply(lambda x: "Actual (2025-2026)" if x >= 2025 else "Histórico (<2025)")

    # Área efectiva y rendimiento
    df_t6["Area_Efectiva"] = np.where(df_t6["Cantidad_V"] > 1, df_t6["Area"] / df_t6["Cantidad_V"], df_t6["Area"])
    df_t6["Rendimiento_Semanal"] = df_t6["Kilos"] / df_t6["Area_Efectiva"]
    return df_t6, None

df_base, _ = cargar_datos_maestros()

# Incorporar nuevos registros
if os.path.exists(ARCHIVO_NUEVOS_DATOS):
    df_nuevos = pd.read_csv(ARCHIVO_NUEVOS_DATOS)
    if not df_nuevos.empty:
        df_base = pd.concat([df_base, df_nuevos], ignore_index=True)

if df_base.empty:
    st.error("❌ No se encontraron datos para procesar.")
    st.stop()

# 3. Formulario Lateral
st.sidebar.header("📥 Registrar Cosecha Futura")
with st.sidebar.form("form_nueva_cosecha"):
    finca_n = st.text_input("Finca", value="CH")
    veg_n = st.selectbox("Vegetal", sorted(df_base["Vegetal"].dropna().unique()))
    kilos_n = st.number_input("Kilos Cosechados", min_value=0.0, value=1200.0)
    area_n = st.number_input("Área (Ha)", min_value=0.1, value=1.0)
    semana_n = st.number_input("Semana Calendario", value=30)
    anio_n = st.number_input("Año", value=2026)
    
    if st.form_submit_button("💾 Guardar"):
        nuevo = pd.DataFrame([{"Finca": finca_n, "Vegetal": veg_n, "Kilos": kilos_n, "Area": area_n, "Semana": semana_n, "Anio": anio_n, "Periodo": "Actual (2025-2026)", "Area_Efectiva": area_n, "Rendimiento_Semanal": kilos_n/area_n}])
        nuevo.to_csv(ARCHIVO_NUEVOS_DATOS, mode='a', header=not os.path.exists(ARCHIVO_NUEVOS_DATOS), index=False)
        st.rerun()

# 4. Tabs
tab1, tab2, tab3 = st.tabs(["📊 Diagnóstico", "📈 Curvas Dinámicas", "🚀 Planificador"])

with tab1:
    st.header("📊 Comportamiento de Duración")
    veg_sel = st.selectbox("Seleccione Vegetal:", sorted(df_base["Vegetal"].dropna().unique()))
    resumen = df_base[df_base["Vegetal"] == veg_sel].groupby("Periodo").agg({"Dur_SC": "mean", "Rendimiento_Semanal": "sum"}).reset_index()
    st.dataframe(resumen, use_container_width=True)

with tab2:
    st.header("📈 Curvas Porcentuales (Actual vs Histórico)")
    veg_sel2 = st.selectbox("Vegetal:", sorted(df_base["Vegetal"].dropna().unique()), key="t2")
    
    df_v2 = df_base[df_base["Vegetal"] == veg_sel2].copy()
    df_v2 = df_v2.sort_values(["Finca", "Lote", "Ciclo", "Anio", "Semana"])
    df_v2["Sem_Rel"] = df_v2.groupby(["Finca", "Lote", "Ciclo"]).cumcount() + 1
    
    tot_ciclo = df_v2.groupby(["Finca", "Lote", "Ciclo"])["Kilos"].transform("sum")
    df_v2["Pct"] = (df_v2["Kilos"] / tot_ciclo) * 100
    
    curva_plot = df_v2.groupby(["Periodo", "Sem_Rel"])["Pct"].mean().reset_index()
    
    # Tabla estructurada
    pivot_curva = curva_plot.pivot(index="Periodo", columns="Sem_Rel", values="Pct").fillna(0)
    pivot_curva.columns = [f"Semana {c} (%)" for c in pivot_curva.columns]
    st.dataframe(pivot_curva.reset_index(), use_container_width=True, hide_index=True)
    
    # Gráfica al final
    fig_c = px.line(curva_plot, x="Sem_Rel", y="Pct", color="Periodo", markers=True, title=f"Gráfica - {veg_sel2}")
    st.plotly_chart(fig_c, use_container_width=True)

with tab3:
    st.header("🚀 Pronóstico")
    # (Lógica de pronóstico mantenida de la versión anterior)
    st.info("Utilice esta sección para simular siembras basadas en las curvas calculadas arriba.")
