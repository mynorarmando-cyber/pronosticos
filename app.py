import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta

# Configuración de página
st.set_page_config(
    page_title="Plataforma de Diagnóstico y Pronóstico Agrícola",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌾 CropPlanner: Diagnóstico Histórico y Simulador de Cosecha")
st.markdown("Sistema integral para entender el comportamiento pasado del lote y proyectar el rendimiento futuro.")

# Función para cargar y procesar datos
@st.cache_data
def cargar_y_procesar_datos():
    # Intenta cargar el archivo de datos principal
    nombre_archivo = 'Analisis final.xlsx'
    try:
        xls = pd.ExcelFile(nombre_archivo)
        df_raw = pd.read_excel(xls, sheet_name=xls.sheet_names[0], skiprows=1)
    except Exception:
        # Fallback a archivos alternativos si cambia el nombre
        df_raw = pd.read_excel('Herramienta_Integral_Analisis_Y_Pronostico_Cosechas.xlsx', skiprows=1)

    t6 = df_raw.iloc[:, 1:14].copy()
    t6.columns = ['Finca', 'Lote', 'Area', 'Ciclo', 'Codigo', 'Vegetal', 'Referencia', 
                  'Cantidad_V', 'Duracion_SC', 'Kilos', 'Semana', 'Ano', 'Mes']
    t6 = t6.dropna(subset=['Finca', 'Ciclo', 'Kilos'])

    for col in ['Area', 'Ciclo', 'Codigo', 'Cantidad_V', 'Duracion_SC', 'Kilos', 'Semana', 'Ano']:
        t6[col] = pd.to_numeric(t6[col], errors='coerce')

    # Ajuste de Área Efectiva y Rendimiento
    t6['Area_Efectiva'] = t6['Area'] / t6['Cantidad_V'].replace(0, 1)
    t6['Rendimiento_Semanal_KgHa'] = t6['Kilos'] / t6['Area_Efectiva']

    # Numeración de Semana Relativa por ciclo
    t6 = t6.sort_values(by=['Finca', 'Lote', 'Ciclo', 'Referencia', 'Codigo'])
    t6['Semana_Relativa'] = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia']).cumcount() + 1

    # Cálculo de Tabla 10 (Consolidado por Ciclo)
    t10 = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia', 'Ano']).agg(
        Area_Total=('Area', 'first'),
        Cantidad_V=('Cantidad_V', 'first'),
        Area_Efectiva=('Area_Efectiva', 'first'),
        Semana_Inicio=('Semana', 'min'),
        Semana_Fin=('Semana', 'max'),
        Duracion_Real_Semanas=('Semana_Relativa', 'max'),
        Kilos_Totales=('Kilos', 'sum')
    ).reset_index()

    t10['Rendimiento_Total_KgHa'] = t10['Kilos_Totales'] / t10['Area_Efectiva']

    # Porcentaje semanal de la curva
    totales_ciclo = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia'])['Kilos'].transform('sum')
    t6['Pct_Cosecha_Semanal'] = (t6['Kilos'] / totales_ciclo) * 100

    return t6, t10

# Cargar datos
try:
    t6, t10 = cargar_y_procesar_datos()
    st.sidebar.success("✅ Base de datos cargada correctamente")
except Exception as e:
    st.error(f"❌ Error al procesar los datos: {e}")
    st.stop()

# Estructura de Pestañas
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 1. Qué Pasó (Histórico)", 
    "📈 2. Curva Adaptativa", 
    "🌤️ 3. Factor Clima / Estación", 
    "🚀 4. Qué Pasará (Simulador)"
])

# -----------------------------------------------------------------------------
# TAB 1: HISTÓRICO (QUÉ PASÓ)
# -----------------------------------------------------------------------------
with tab1:
    st.header("Análisis Histórico de Rendimientos y Ciclos")
    
    col_f1, col_f2 = st.columns(2)
    ref_sel = col_f1.selectbox("Filtrar por Referencia / Cultivo:", sorted(t10['Referencia'].dropna().unique()))
    finca_sel = col_f2.multiselect("Filtrar por Finca:", sorted(t10['Finca'].dropna().unique()), default=sorted(t10['Finca'].dropna().unique()))

    t10_filt = t10[(t10['Referencia'] == ref_sel) & (t10['Finca'].isin(finca_sel))]
    t6_filt = t6[(t6['Referencia'] == ref_sel) & (t6['Finca'].isin(finca_sel))]

    # Métricas Clave
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Ciclos Registrados", len(t10_filt))
    m2.metric("Rendimiento Promedio", f"{t10_filt['Rendimiento_Total_KgHa'].mean():,.1f} Kg/Ha")
    m3.metric("Duración Promedio Real", f"{t10_filt['Duracion_Real_Semanas'].mean():.1f} Semanas")
    m4.metric("Total Kilos Históricos", f"{t10_filt['Kilos_Totales'].sum():,.0f} Kg")

    st.markdown("---")
    
    # Gráfico Rendimiento Histórico por Año
    fig_rend = px.box(
        t10_filt, x='Ano', y='Rendimiento_Total_KgHa', color='Ano',
        title=f"Evolución del Rendimiento por Hectárea ({ref_sel}) por Año",
        labels={'Rendimiento_Total_KgHa': 'Rendimiento (Kg/Ha)', 'Ano': 'Año'}
    )
    st.plotly_chart(fig_rend, use_container_width=True)

    # Detalle de Tabla 10
    st.subheader("📋 Consolidado de Ciclos (Tabla 10)")
    st.dataframe(
        t10_filt[['Finca', 'Lote', 'Ciclo', 'Ano', 'Area_Efectiva', 'Duracion_Real_Semanas', 'Kilos_Totales', 'Rendimiento_Total_KgHa']],
        use_container_width=True
    )

# -----------------------------------------------------------------------------
# TAB 2: CURVA ADAPTATIVA (DURACIÓN DE COSECHA)
# -----------------------------------------------------------------------------
with tab2:
    st.header("Análisis de Curva de Producción: Histórica vs. Actual")
    st.markdown("Comparativa de patrones entre años antiguos (≤ 2023) y recientes (≥ 2024) para capturar cambios de duración.")

    curva_hist = t6_filt[t6_filt['Ano'] <= 2023].groupby('Semana_Relativa')['Pct_Cosecha_Semanal'].mean().reset_index()
    curva_rec = t6_filt[t6_filt['Ano'] >= 2024].groupby('Semana_Relativa')['Pct_Cosecha_Semanal'].mean().reset_index()

    fig_curva = go.Figure()
    fig_curva.add_trace(go.Scatter(
        x=curva_hist['Semana_Relativa'], y=curva_hist['Pct_Cosecha_Semanal'],
        mode='lines+markers', name='Curva Histórica (≤ 2023)', line=dict(color='gray', dash='dash')
    ))
    fig_curva.add_trace(go.Scatter(
        x=curva_rec['Semana_Relativa'], y=curva_rec['Pct_Cosecha_Semanal'],
        mode='lines+markers', name='Curva Reciente / Actual (≥ 2024)', line=dict(color='green', width=3)
    ))

    fig_curva.update_layout(
        title=f"Distribución Semanal de Cosecha (% del Total) - {ref_sel}",
        xaxis_title="Semana Relativa de Cosecha (Semana 1, 2, 3...)",
        yaxis_title="% Cosechado del Total del Ciclo",
        template="plotly_white"
    )
    st.plotly_chart(fig_curva, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: FACTOR CLIMA Y ESTACIONALIDAD
# -----------------------------------------------------------------------------
with tab3:
    st.header("Comportamiento por Época / Semana Calendario")
    st.markdown("Variación del rendimiento semanal según las 52 semanas del año.")

    estacion = t6_filt.groupby('Semana')['Rendimiento_Semanal_KgHa'].mean().reset_index()
    rend_global = estacion['Rendimiento_Semanal_KgHa'].mean()
    estacion['Indice_Estacional'] = estacion['Rendimiento_Semanal_KgHa'] / rend_global

    fig_est = px.bar(
        estacion, x='Semana', y='Indice_Estacional',
        title=f"Índice Estacional por Semana Calendario (1.0 = Promedio Global) - {ref_sel}",
        labels={'Semana': 'Semana del Año (1 a 52)', 'Indice_Estacional': 'Factor de Ajuste Estacional'},
        color='Indice_Estacional', color_continuous_scale='RdYlGn'
    )
    fig_est.add_hline(y=1.0, line_dash="dash", line_color="black", annotation_text="Base 1.0")
    st.plotly_chart(fig_est, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 4: SIMULADOR FUTURO (QUÉ PASARÁ)
# -----------------------------------------------------------------------------
with tab4:
    st.header("🚀 Proyección y Pronóstico de Nueva Siembra")
    
    col_p1, col_p2, col_p3 = st.columns(3)
    veg_sim = col_p1.selectbox("Vegetal / Referencia:", sorted(t6['Referencia'].unique()), key="sim_veg")
    area_sim = col_p2.number_input("Área a Sembrar (Hectáreas Efectivas):", min_value=0.1, max_value=500.0, value=5.0, step=0.5)
    fecha_sim = col_p3.date_input("Fecha Estimada de Siembra:", value=pd.to_datetime('2026-09-01'))

    # Configuración de curva recomendada
    st.subheader("⚙️ Configuración del Modelo Recomendado")
    usar_reciente = st.checkbox("Usar Curva Adaptativa Reciente (Recomendado para Brócoli de 6-7 semanas)", value=True)

    if st.button("📊 Generar Proyección Futura"):
        t6_v = t6[t6['Referencia'] == veg_sim]
        t10_v = t10[t10['Referencia'] == veg_sim]

        # 1. Base de rendimiento
        p25 = np.percentile(t10_v['Rendimiento_Total_KgHa'].dropna(), 25)
        p50 = np.percentile(t10_v['Rendimiento_Total_KgHa'].dropna(), 50)
        p75 = np.percentile(t10_v['Rendimiento_Total_KgHa'].dropna(), 75)

        # 2. Selección de Curva
        if usar_reciente:
            c_data = t6_v[t6_v['Ano'] >= 2024]
            if c_data.empty: c_data = t6_v
        else:
            c_data = t6_v

        curva_base = c_data.groupby('Semana_Relativa')['Pct_Cosecha_Semanal'].mean().reset_index()
        curva_base['Pct_Norm'] = curva_base['Pct_Cosecha_Semanal'] / curva_base['Pct_Cosecha_Semanal'].sum()

        # 3. Mapeo Temporal
        fecha_ini_cos = pd.to_datetime(fecha_sim) + timedelta(days=60)
        sem_ini = fecha_ini_cos.isocalendar()[1]

        res_list = []
        for _, r in curva_base.iterrows():
            s_rel = int(r['Semana_Relativa'])
            pct = r['Pct_Norm']
            s_cal = (sem_ini + s_rel - 1) % 52
            if s_cal == 0: s_cal = 52

            # Factor de estacionalidad
            idx_est = estacion[estacion['Semana'] == s_cal]['Indice_Estacional'].values
            f_est = idx_est[0] if len(idx_est) > 0 else 1.0

            kg_p25 = area_sim * p25 * pct * f_est
            kg_p50 = area_sim * p50 * pct * f_est
            kg_p75 = area_sim * p75 * pct * f_est

            res_list.append({
                'Semana Relativa': s_rel,
                'Semana Calendario': s_cal,
                '% Distribución': round(pct * 100, 2),
                'Factor Estacional': round(f_est, 2),
                'Kg Conservador (P25)': round(kg_p25, 1),
                'Kg Probable (P50)': round(kg_p50, 1),
                'Kg Optimista (P75)': round(kg_p75, 1)
            })

        df_proy = pd.DataFrame(res_list)

        # Resultados Totales
        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Proyección Probable (P50)", f"{df_proy['Kg Probable (P50)'].sum():,.1f} Kg")
        r2.metric("Escenario Conservador (P25)", f"{df_proy['Kg Conservador (P25)'].sum():,.1f} Kg")
        r3.metric("Escenario Optimista (P75)", f"{df_proy['Kg Optimista (P75)'].sum():,.1f} Kg")
        r4.metric("Duración Estimada", f"{len(df_proy)} Semanas")

        # Gráfico de la Proyección Futura
        fig_proy = go.Figure()
        fig_proy.add_trace(go.Bar(x=df_proy['Semana Calendario'], y=df_proy['Kg Conservador (P25)'], name='P25 (Conservador)', marker_color='#FFA500'))
        fig_proy.add_trace(go.Bar(x=df_proy['Semana Calendario'], y=df_proy['Kg Probable (P50)'], name='P50 (Probable)', marker_color='#2E8B57'))
        fig_proy.add_trace(go.Bar(x=df_proy['Semana Calendario'], y=df_proy['Kg Optimista (P75)'], name='P75 (Optimista)', marker_color='#4682B4'))

        fig_proy.update_layout(
            title=f"Pronóstico Semanal de Cosecha - {veg_sim} ({area_sim} Ha)",
            xaxis_title="Semana Calendario del Año",
            yaxis_title="Kilogramos Cosechados",
            barmode='group',
            template="plotly_white"
        )
        st.plotly_chart(fig_proy, use_container_width=True)

        st.subheader("📅 Plan de Cosecha Semanal Proyectado")
        st.dataframe(df_proy, use_container_width=True)
