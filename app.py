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

st.title(
    "🌾 CropPlanner: Planificador Inteligente y Curvas de Cosecha Dinámicas"
)
st.markdown(
    "Sistema conectado al archivo maestro para análisis histórico, cálculo"
    " adaptativo de duración y pronóstico de siembras futuras."
)

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
  df_t6.columns = [
      "Finca",
      "Lote",
      "Area",
      "Ciclo",
      "Codigo",
      "Vegetal",
      "Referencia",
      "Cantidad_V",
      "Dur_SC",
      "Kilos",
      "Semana",
      "Anio",
      "Mes",
  ]

  for col in [
      "Area",
      "Ciclo",
      "Codigo",
      "Cantidad_V",
      "Dur_SC",
      "Kilos",
      "Semana",
      "Anio",
  ]:
    df_t6[col] = pd.to_numeric(df_t6[col], errors="coerce")

  df_t6 = df_t6.dropna(subset=["Vegetal", "Ciclo", "Kilos"])
  df_t6["Periodo"] = df_t6["Anio"].apply(
      lambda x: "Actual (2025-2026)" if x >= 2025 else "Histórico (<2025)"
  )

  # Área efectiva y rendimiento semanal por Ha
  df_t6["Area_Efectiva"] = np.where(
      df_t6["Cantidad_V"] > 1,
      df_t6["Area"] / df_t6["Cantidad_V"],
      df_t6["Area"],
  )
  df_t6["Rendimiento_Semanal"] = df_t6["Kilos"] / df_t6["Area_Efectiva"]

  # --- TABLA 10 (Consolidado) ---
  df_t10 = df_raw.iloc[1:, 15:26].copy()
  if df_t10.shape[1] >= 11:
    df_t10.columns = [
        "Finca",
        "Lote",
        "Area",
        "Ciclo",
        "Vegetal",
        "Referencia",
        "Cantidad_V",
        "Dur_SC",
        "Total_Kilos",
        "Rendimiento",
        "Rendimiento_Real",
    ]
    for col in [
        "Area",
        "Ciclo",
        "Cantidad_V",
        "Dur_SC",
        "Total_Kilos",
        "Rendimiento",
        "Rendimiento_Real",
    ]:
      df_t10[col] = pd.to_numeric(df_t10[col], errors="coerce")
    df_t10["Periodo"] = "Global"
  else:
    df_t10 = pd.DataFrame()

  return df_t6, df_t10


df_base, df_t10 = cargar_datos_maestros()

# Incorporar nuevos registros guardados por el usuario si existen
if os.path.exists(ARCHIVO_NUEVOS_DATOS):
  df_nuevos = pd.read_csv(ARCHIVO_NUEVOS_DATOS)
  if not df_nuevos.empty:
    df_base = pd.concat([df_base, df_nuevos], ignore_index=True)

if df_base.empty:
  st.error(
      "❌ No se encontraron datos para procesar. Verifique el archivo"
      " Analisis final.xlsx"
  )
  st.stop()

# 3. Formulario Lateral: Ingesta Continua para Nuevas Semanas
st.sidebar.header("📥 Registrar Cosecha Futura")
with st.sidebar.form("form_nueva_cosecha"):
  st.markdown("Alimenta el sistema con los datos de las próximas semanas:")
  finca_n = st.text_input("Finca", value="CH")
  lote_n = st.text_input("Lote", value="CH01")
  veg_n = st.selectbox(
      "Vegetal", sorted(df_base["Vegetal"].dropna().unique())
  )
  area_n = st.number_input("Área (Ha)", min_value=0.1, value=1.0)
  ciclo_n = st.number_input("Ciclo", min_value=1, value=15, step=1)
  codigo_n = st.number_input(
      "Código (Semana Relativa de Cosecha)", min_value=1, value=1, step=1
  )
  kilos_n = st.number_input("Kilos Cosechados", min_value=0.0, value=1200.0)
  semana_n = st.number_input(
      "Semana Calendario", min_value=1, max_value=52, value=30
  )
  anio_n = st.number_input("Año", min_value=2025, max_value=2030, value=2026)

  btn_guardar = st.form_submit_button("💾 Guardar y Actualizar Modelo")

if btn_guardar:
  nuevo_registro = pd.DataFrame([{
      "Finca": finca_n,
      "Lote": lote_n,
      "Area": area_n,
      "Ciclo": ciclo_n,
      "Codigo": codigo_n,
      "Vegetal": veg_n,
      "Referencia": veg_n,
      "Cantidad_V": 1,
      "Dur_SC": codigo_n,
      "Kilos": kilos_n,
      "Semana": semana_n,
      "Anio": anio_n,
      "Mes": "Actual",
      "Periodo": "Actual (2025-2026)",
      "Area_Efectiva": area_n,
      "Rendimiento_Semanal": kilos_n / area_n,
  }])

  if os.path.exists(ARCHIVO_NUEVOS_DATOS):
    df_existente = pd.read_csv(ARCHIVO_NUEVOS_DATOS)
    df_actualizado = pd.concat(
        [df_existente, nuevo_registro], ignore_index=True
    )
  else:
    df_actualizado = nuevo_registro

  df_actualizado.to_csv(ARCHIVO_NUEVOS_DATOS, index=False)
  st.sidebar.success(
      "✅ ¡Registro guardado! Las curvas y pronósticos se han recalculado"
      " automáticamente."
  )
  st.rerun()

# 4. Pestañas de Análisis y Pronóstico
tab1, tab2, tab3 = st.tabs([
    "📊 Diagnóstico Histórico y Duración Real",
    "📈 Curvas Porcentuales Dinámicas",
    "🚀 Planificador de Siembra y Pronóstico",
])

# -----------------------------------------------------------------------------
# TAB 1: DIAGNÓSTICO HISTÓRICO Y DURACIÓN REAL
# -----------------------------------------------------------------------------
with tab1:
  st.header("📊 Comportamiento de Duración y Rendimiento por Cultivo")
  lista_veg = sorted(df_base["Vegetal"].dropna().unique())
  veg_sel1 = st.selectbox("Seleccione Vegetal:", lista_veg, key="t1_v")

  df_v1 = df_base[df_base["Vegetal"] == veg_sel1]
  resumen_v = (
      df_v1.groupby("Periodo")
      .agg(
          Ciclos_Totales=("Ciclo", "nunique"),
          Duracion_Promedio=("Dur_SC", "mean"),
          Rendimiento_Total_Promedio=("Rendimiento_Semanal", "sum"),
      )
      .reset_index()
  )

  st.dataframe(resumen_v, use_container_width=True, hide_index=True)

  fig_d = px.bar(
      resumen_v,
      x="Periodo",
      y="Duracion_Promedio",
      color="Periodo",
      text_auto=".1f",
      title=f"Evolución de la Duración del Ciclo (Semanas) - {veg_sel1}",
  )
  st.plotly_chart(fig_d, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: CURVAS PORCENTUALES DINÁMICAS (TABLA PRIMERO, GRÁFICA AL FINAL)
# -----------------------------------------------------------------------------
with tab2:
  st.header(
      "📈 Curvas Porcentuales de Cosecha (Actual vs Histórico por Semana)"
  )
  veg_sel2 = st.selectbox("Seleccione Vegetal:", lista_veg, key="t2_v")

  df_v2 = df_base[df_base["Vegetal"] == veg_sel2].copy()
  df_v2 = df_v2.sort_values(["Finca", "Lote", "Ciclo", "Anio", "Semana"])
  df_v2["Sem_Rel"] = (
      df_v2.groupby(["Finca", "Lote", "Ciclo"]).cumcount() + 1
  )

  # Normalizar porcentaje por ciclo
  tot_ciclo = df_v2.groupby(["Finca", "Lote", "Ciclo"])["Kilos"].transform(
      "sum"
  )
  df_v2["Pct"] = (
      df_v2["Kilos"] / tot_ciclo
  ) * 100  # Convertir a porcentaje 0-100

  curva_plot = (
      df_v2.groupby(["Periodo", "Sem_Rel"])["Pct"].mean().reset_index()
  )

  # Crear tabla pivote con Periodo en filas y las Semanas (1, 2, 3...) en columnas con sus porcentajes
  pivot_curva = curva_plot.pivot(
      index="Periodo", columns="Sem_Rel", values="Pct"
  ).fillna(0)
  pivot_curva.columns = [f"Semana {c} (%)" for c in pivot_curva.columns]

  st.markdown(
      "**Tabla Comparativa por Periodo (Filas: Periodos | Columnas: Porcentaje"
      " por Semana):**"
  )
  st.dataframe(pivot_curva, use_container_width=True)

  st.markdown("---")

  # Gráfica colocada al final
  fig_c = px.line(
      curva_plot,
      x="Sem_Rel",
      y="Pct",
      color="Periodo",
      markers=True,
      title=f"Gráfica de Distribución Semanal (% de Cosecha) - {veg_sel2}",
      labels={
          "Sem_Rel": "Semana de Cosecha en el Ciclo",
          "Pct": "Porcentaje del Total (%)",
      },
  )
  st.plotly_chart(fig_c, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: PLANIFICADOR DE SIEMBRA Y PRONÓSTICO
# -----------------------------------------------------------------------------
with tab3:
  st.header(
      "🚀 Planificador de Siembra: Pronóstico de Kilos Semana a Semana"
  )

  col_p1, col_p2, col_p3 = st.columns(3)
  veg_plan = col_p1.selectbox("Vegetal a Planificar:", lista_veg, key="p_veg")
  area_plan = col_p2.number_input("Área Propuesta (Ha):", min_value=0.1, value=3.0)
  periodo_plan = col_p3.radio(
      "Tomar Base de Rendimiento:", ["Actual (2025-2026)", "Histórico (<2025)"]
  )

  if st.button("🎯 Calcular Proyección Futura"):
    df_p_base = df_base[
        (df_base["Vegetal"] == veg_plan)
        & (df_base["Periodo"] == periodo_plan)
    ]
    if df_p_base.empty:
      df_p_base = df_base[df_base["Vegetal"] == veg_plan]

    rend_prom = df_p_base["Rendimiento_Semanal"].sum() / max(
        1, df_p_base["Ciclo"].nunique()
    )
    kilos_est_totales = area_plan * rend_prom

    df_p_curva = df_base[
        (df_base["Vegetal"] == veg_plan)
        & (df_base["Periodo"] == periodo_plan)
    ].copy()
    if not df_p_curva.empty:
      df_p_curva = df_p_curva.sort_values(
          ["Finca", "Lote", "Ciclo", "Anio", "Semana"]
      )
      df_p_curva["Sem_Rel"] = (
          df_p_curva.groupby(["Finca", "Lote", "Ciclo"]).cumcount() + 1
      )
      tot_c = df_p_curva.groupby(["Finca", "Lote", "Ciclo"])[
          "Kilos"
      ].transform("sum")
      df_p_curva["Pct_Norm"] = df_p_curva["Kilos"] / tot_c
      curva_res = (
          df_p_curva.groupby("Sem_Rel")["Pct_Norm"].mean().reset_index()
      )
    else:
      curva_res = pd.DataFrame(
          {
              "Sem_Rel": [1, 2, 3, 4, 5, 6],
              "Pct_Norm": [0.2, 0.25, 0.2, 0.15, 0.1, 0.1],
          }
      )

    curva_res["Kilos_Estimados"] = curva_res["Pct_Norm"] * kilos_est_totales
    curva_res["Porcentaje (%)"] = curva_res["Pct_Norm"] * 100

    st.success(
        f"✅ Pronóstico generado para **{area_plan} Ha** de **{veg_plan}**"
        f" usando el periodo **{periodo_plan}**:"
        f" **{kilos_est_totales:,.2f} Kilos Totales Proyectados**"
    )

    st.markdown("**Tabla de Distribución Proyectada:**")
    st.dataframe(
        curva_res[
            ["Sem_Rel", "Porcentaje (%)", "Kilos_Estimados"]
        ].rename(columns={"Sem_Rel": "Semana de Cosecha"}),
        use_container_width=True,
        hide_index=True,
    )

    fig_proy = px.bar(
        curva_res,
        x="Sem_Rel",
        y="Kilos_Estimados",
        text_auto=".1f",
        title=f"Distribución Semanal Proyectada para la Nueva Siembra ({veg_plan})",
        labels={
            "Sem_Rel": "Semana de Cosecha",
            "Kilos_Estimados": "Kilos Estimados",
        },
        color_discrete_sequence=["#2E8B57"],
    )
    st.plotly_chart(fig_proy, use_container_width=True)
