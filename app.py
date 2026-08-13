import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. Configuración de la aplicación
st.set_page_config(
    page_title='CropPlanner - Plataforma Agrícola Integral',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.title('🌾 CropPlanner: Análisis Comparativo y Simulador Agrícola')
st.markdown(
    'Módulo de diagnóstico comparativo de curvas de producción (**General**,'
    ' **< 2025** y **2025-2026**) e ingesta continua de nuevos datos.'
)


# 2. Carga y Procesamiento de Datos
@st.cache_data
def cargar_base_datos():
  # Cargar desde los archivos del proyecto
  archivo_matriz = 'Matris recomendada.xlsx'
  archivo_hist = 'Herramienta_Integral_Analisis_Y_Pronostico_Cosechas.xlsx'

  if os.path.exists(archivo_hist):
    xls_h = pd.ExcelFile(archivo_hist)
    df_h = pd.read_excel(xls_h, sheet_name='Historico Real Semanal')
    t6 = df_h.iloc[2:].copy()
    t6.columns = df_h.iloc[1].values

    for c in [
        'Area (Ha)',
        'Cantidad V',
        'Area Efectiva (Ha)',
        'Ciclo',
        'Codigo',
        'Kilos',
        'Semana Calendario',
        'Ano',
        'Semana Corte (Ciclo)',
        'Rendimiento Real (Kg/Ha)',
    ]:
      t6[c] = pd.to_numeric(t6[c], errors='coerce')

    t6 = t6.dropna(subset=['Finca', 'Ciclo', 'Kilos', 'Referencia'])
    tot_ciclo = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia'])[
        'Kilos'
    ].transform('sum')
    t6['Pct_Cosecha_Semanal'] = (t6['Kilos'] / tot_ciclo) * 100
  else:
    t6 = pd.DataFrame()

  return t6


t6_data = cargar_base_datos()

# 3. Formulario en la Barra Lateral para Registro Continuo de Datos Futuros
st.sidebar.header('📝 Captura Cosecha Futura (2026+)')
with st.sidebar.form('form_cosecha_futura'):
  st.markdown('**Agregar Nuevo Corte Real**')
  finca_f = st.text_input('Finca', value='CH')
  lote_f = st.text_input('Lote', value='CH01')
  veg_f = st.selectbox(
      'Vegetal / Referencia',
      ['Broccoli', 'Fino', 'Dulce', 'China', 'Esparrago', 'Grano', 'Zanahoria'],
  )
  area_f = st.number_input('Área (Ha)', min_value=0.1, value=1.0, step=0.1)
  cant_v_f = st.number_input('Cantidad V', min_value=1, value=1, step=1)
  ciclo_f = st.number_input('Ciclo', min_value=1, value=10, step=1)
  codigo_f = st.number_input('Código / Corte', min_value=1, value=1, step=1)
  ano_f = st.number_input(
      'Año', min_value=2025, max_value=2030, value=2026, step=1
  )
  semana_f = st.number_input(
      'Semana Calendario (1-52)', min_value=1, max_value=52, value=10, step=1
  )
  sem_corte_f = st.number_input(
      'Semana Corte (Ciclo)', min_value=1, max_value=20, value=1, step=1
  )
  kilos_f = st.number_input('Kilos Cosechados', min_value=0.0, value=1000.0)

  guardar = st.form_submit_button('💾 Guardar Cosecha')

if guardar:
  area_efectiva = area_f / cant_v_f
  rend_real = kilos_f / area_efectiva if area_efectiva > 0 else 0
  nuevo_registro = pd.DataFrame([{
      'Finca': finca_f,
      'Lote': lote_f,
      'Area (Ha)': area_f,
      'Cantidad V': cant_v_f,
      'Area Efectiva (Ha)': area_efectiva,
      'Ciclo': ciclo_f,
      'Codigo': codigo_f,
      'Vegetal': veg_f,
      'Referencia': veg_f,
      'Kilos': kilos_f,
      'Semana Calendario': semana_f,
      'Ano': ano_f,
      'Mes': 'N/A',
      'Semana Corte (Ciclo)': sem_corte_f,
      'Rendimiento Real (Kg/Ha)': rend_real,
  }])
  t6_data = pd.concat([t6_data, nuevo_registro], ignore_index=True)
  st.sidebar.success('✅ Registro guardado exitosamente.')

# 4. Estructura Principal en Pestañas
tab1, tab2, tab3 = st.tabs([
    '📊 Comportamiento Comparativo por Vegetal',
    '📈 Curvas Porcentuales de Producción',
    '🚀 Simulador de Pronósticos Futuros',
])

# -----------------------------------------------------------------------------
# TAB 1: COMPORTAMIENTO COMPARATIVO GENERAL VS <2025 VS 2025-2026
# -----------------------------------------------------------------------------
with tab1:
  st.header('📊 Comportamiento Comparativo y Duración Real por Cultivo')
  st.markdown(
      'Comparativa de Rendimientos Medios y Duración en Semanas entre los 3'
      ' periodos requeridos.'
  )

  if not t6_data.empty:
    veg_sel = st.selectbox(
        'Selecciona Vegetal para Inspeccionar:',
        sorted(t6_data['Referencia'].dropna().unique()),
    )

    t6_veg = t6_data[t6_data['Referencia'] == veg_sel].copy()

    # Asignación de periodos
    t6_veg_hist = t6_veg[t6_veg['Ano'] < 2025]
    t6_veg_act = t6_veg[t6_veg['Ano'] >= 2025]

    # Cálculos por ciclo
    def calcular_resumen_ciclos(df_sub):
      if df_sub.empty:
        return {'Ciclos': 0, 'Duracion_Prom': 0.0, 'Rend_Prom': 0.0}
      ciclos = df_sub.groupby(['Finca', 'Lote', 'Ciclo']).agg(
          Kilos_Tot=('Kilos', 'sum'),
          Area_Ef=('Area Efectiva (Ha)', 'first'),
          Duracion=('Semana Corte (Ciclo)', 'max'),
      )
      ciclos['Rend_KgHa'] = ciclos['Kilos_Tot'] / ciclos['Area_Ef']
      return {
          'Ciclos': len(ciclos),
          'Duracion_Prom': ciclos['Duracion'].mean(),
          'Rend_Prom': ciclos['Rend_KgHa'].mean(),
      }

    res_gen = calcular_resumen_ciclos(t6_veg)
    res_hist = calcular_resumen_ciclos(t6_veg_hist)
    res_act = calcular_resumen_ciclos(t6_veg_act)

    # Mostrar Tabla Resumen
    df_comp_resumen = pd.DataFrame([
        {
            'Periodo': 'Comportamiento General (Promedio Histórico Total)',
            'Ciclos Totales': res_gen['Ciclos'],
            'Duración Promedio (Semanas)': round(res_gen['Duracion_Prom'], 2),
            'Rendimiento Promedio (Kg/Ha)': round(res_gen['Rend_Prom'], 1),
        },
        {
            'Periodo': 'Histórico (< 2025)',
            'Ciclos Totales': res_hist['Ciclos'],
            'Duración Promedio (Semanas)': round(res_hist['Duracion_Prom'], 2),
            'Rendimiento Promedio (Kg/Ha)': round(res_hist['Rend_Prom'], 1),
        },
        {
            'Periodo': 'Comportamiento Actual (2025 - 2026+)',
            'Ciclos Totales': res_act['Ciclos'],
            'Duración Promedio (Semanas)': round(res_act['Duracion_Prom'], 2),
            'Rendimiento Promedio (Kg/Ha)': round(res_act['Rend_Prom'], 1),
        },
    ])

    st.subheader(f'📋 Tabla Resumen Comparativa: {veg_sel}')
    st.dataframe(df_comp_resumen, use_container_width=True)

    # Gráfico de Barras de Rendimiento Comparativo
    fig_rend_comp = px.bar(
        df_comp_resumen,
        x='Periodo',
        y='Rendimiento Promedio (Kg/Ha)',
        color='Periodo',
        text_auto='.1f',
        title=f'Comparativa de Rendimiento (Kg/Ha) por Periodo - {veg_sel}',
        color_discrete_sequence=['#2E8B57', '#4682B4', '#E67E22'],
    )
    st.plotly_chart(fig_rend_comp, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: CURVAS DE DISTRIBUCIÓN PORCENTUAL SEMANAL
# -----------------------------------------------------------------------------
with tab2:
  st.header('📈 Curvas de Distribución Porcentual Semanal (% Cosechado)')
  st.markdown(
      'Evaluación de cómo se distribuye la cosecha semana a semana'
      ' comparando los tres periodos.'
  )

  if not t6_data.empty:
    # Recalcular % semanal por ciclo
    totales_ciclo = t6_veg.groupby(['Finca', 'Lote', 'Ciclo'])[
        'Kilos'
    ].transform('sum')
    t6_veg['Pct_Cosecha'] = (t6_veg['Kilos'] / totales_ciclo) * 100

    curva_gen = (
        t6_veg.groupby('Semana Corte (Ciclo)')['Pct_Cosecha']
        .mean()
        .reset_index()
    )
    curva_hist = (
        t6_veg[t6_veg['Ano'] < 2025]
        .groupby('Semana Corte (Ciclo)')['Pct_Cosecha']
        .mean()
        .reset_index()
    )
    curva_act = (
        t6_veg[t6_veg['Ano'] >= 2025]
        .groupby('Semana Corte (Ciclo)')['Pct_Cosecha']
        .mean()
        .reset_index()
    )

    fig_curvas_comp = go.Figure()
    fig_curvas_comp.add_trace(
        go.Scatter(
            x=curva_gen['Semana Corte (Ciclo)'],
            y=curva_gen['Pct_Cosecha'],
            mode='lines+markers',
            name='General Promedio',
            line=dict(color='#2E8B57', width=3),
        )
    )
    fig_curvas_comp.add_trace(
        go.Scatter(
            x=curva_hist['Semana Corte (Ciclo)'],
            y=curva_hist['Pct_Cosecha'],
            mode='lines+markers',
            name='Histórico (< 2025)',
            line=dict(color='#4682B4', dash='dash'),
        )
    )
    fig_curvas_comp.add_trace(
        go.Scatter(
            x=curva_act['Semana Corte (Ciclo)'],
            y=curva_act['Pct_Cosecha'],
            mode='lines+markers',
            name='Actual (2025 - 2026+)',
            line=dict(color='#E67E22', width=3),
        )
    )

    fig_curvas_comp.update_layout(
        title=f'Curva de Producción Porcentual - {veg_sel}',
        xaxis_title='Semana Relativa de Corte (Semana 1, 2, 3...)',
        yaxis_title='% del Total Cosechado',
        template='plotly_white',
    )
    st.plotly_chart(fig_curvas_comp, use_container_width=True)

    # Tabla Unificada de Porcentajes
    df_curva_tab = pd.merge(
        curva_gen,
        curva_hist,
        on='Semana Corte (Ciclo)',
        how='outer',
        suffixes=(' General', ' <2025'),
    )
    df_curva_tab = pd.merge(
        df_curva_tab,
        curva_act,
        on='Semana Corte (Ciclo)',
        how='outer',
    ).rename(columns={'Pct_Cosecha': 'Pct 2025-2026'})
    df_curva_tab = df_curva_tab.sort_values(
        by='Semana Corte (Ciclo)'
    ).fillna(0)

    st.subheader('📋 Porcentajes Semanales por Periodo')
    st.dataframe(df_curva_tab, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: SIMULADOR DE PRONÓSTICOS FUTUROS
# -----------------------------------------------------------------------------
with tab3:
  st.header('🚀 Proyección Futura de Producción')

  col_s1, col_s2, col_s3 = st.columns(3)
  veg_sim = col_s1.selectbox(
      'Vegetal a Planificar:',
      sorted(t6_data['Referencia'].dropna().unique()),
      key='sim_v',
  )
  area_sim = col_s2.number_input(
      'Área a Sembrar (Hectáreas):',
      min_value=0.1,
      max_value=500.0,
      value=5.0,
  )
  modelo_curva = col_s3.radio(
      'Curva Base a Aplicar:',
      ['Comportamiento Actual (2025-2026)', 'Histórico (<2025)', 'General'],
  )

  if st.button('🎯 Proyectar Cosecha'):
    t6_sim = t6_data[t6_data['Referencia'] == veg_sim]

    if modelo_curva == 'Comportamiento Actual (2025-2026)':
      sub = t6_sim[t6_sim['Ano'] >= 2025]
      if sub.empty:
        sub = t6_sim
    elif modelo_curva == 'Histórico (<2025)':
      sub = t6_sim[t6_sim['Ano'] < 2025]
    else:
      sub = t6_sim

    curva_p = (
        sub.groupby('Semana Corte (Ciclo)')['Pct_Cosecha_Semanal']
        .mean()
        .reset_index()
    )
    curva_p['Factor'] = (
        curva_p['Pct_Cosecha_Semanal'] / curva_p['Pct_Cosecha_Semanal'].sum()
    )

    # Rendimiento promedio por ciclo
    cic_sub = sub.groupby(['Finca', 'Lote', 'Ciclo']).agg(
        K=('Kilos', 'sum'), A=('Area Efectiva (Ha)', 'first')
    )
    rend_base = (cic_sub['K'] / cic_sub['A']).mean()

    kilos_totales_est = area_sim * rend_base

    curva_p['Kilos Proyectados'] = curva_p['Factor'] * kilos_totales_est

    st.success(
        f'Proyección Total Estimada para {area_sim} Ha de {veg_sim}:'
        f' **{kilos_totales_est:,.1f} Kg**'
    )

    fig_sim = px.bar(
        curva_p,
        x='Semana Corte (Ciclo)',
        y='Kilos Proyectados',
        text_auto='.1f',
        title=f'Distribución Semanal Estimada ({modelo_curva})',
        color_discrete_sequence=['#2E8B57'],
    )
    st.plotly_chart(fig_sim, use_container_width=True)

    st.dataframe(curva_p, use_container_width=True)
