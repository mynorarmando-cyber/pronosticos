import os
import unicodedata
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. Configuración de la página
st.set_page_config(
    page_title='CropPlanner - Plataforma Agrícola Integral',
    layout='wide',
    initial_sidebar_state='expanded',
)

st.title('🌾 CropPlanner: Análisis Comparativo y Simulador Agrícola')
st.markdown(
    'Módulo de diagnóstico comparativo de curvas de producción (**General**,'
    ' **< 2025** y **2025-2026**) e ingesta continua de datos.'
)


# Función auxiliar para limpiar nombres de columnas
def limpiar_texto(texto):
  if not isinstance(texto, str):
    return str(texto)
  texto = unicodedata.normalize('NFKD', texto)
  texto = ''.join([c for c in texto if not unicodedata.combining(c)])
  return texto.strip()


# 2. Carga y Procesamiento Seguro de Datos
@st.cache_data
def cargar_base_datos():
  archivo_hist = 'Herramienta_Integral_Analisis_Y_Pronostico_Cosechas.xlsx'

  if os.path.exists(archivo_hist):
    xls_h = pd.ExcelFile(archivo_hist)
    df_h = pd.read_excel(xls_h, sheet_name='Historico Real Semanal')

    # Encabezados en la fila 1
    t6 = df_h.iloc[2:].copy()
    col_names = [limpiar_texto(col) for col in df_h.iloc[1].values]
    t6.columns = col_names

    # Estandarización de columnas numéricas clave
    columnas_num = [
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
    ]

    for col in columnas_num:
      if col in t6.columns:
        t6[col] = pd.to_numeric(t6[col], errors='coerce')

    # Mapeo flexible de columnas esenciales
    col_ref = 'Referencia' if 'Referencia' in t6.columns else 'Vegetal'
    t6['Referencia'] = t6[col_ref] if col_ref in t6.columns else 'Sin Registro'

    # Limpieza de nulos
    t6 = t6.dropna(subset=['Kilos', 'Referencia', 'Ciclo'])

    # Cálculo seguro de % de cosecha
    if all(
        c in t6.columns for c in ['Finca', 'Lote', 'Ciclo', 'Referencia', 'Kilos']
    ):
      tot_ciclo = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia'])[
          'Kilos'
      ].transform('sum')
      t6['Pct_Cosecha_Semanal'] = np.where(
          tot_ciclo > 0, (t6['Kilos'] / tot_ciclo) * 100, 0
      )
    else:
      t6['Pct_Cosecha_Semanal'] = 0.0

    return t6
  else:
    # DataFrame por defecto si no encuentra el Excel
    return pd.DataFrame(
        columns=[
            'Finca',
            'Lote',
            'Area (Ha)',
            'Cantidad V',
            'Area Efectiva (Ha)',
            'Ciclo',
            'Codigo',
            'Referencia',
            'Kilos',
            'Semana Calendario',
            'Ano',
            'Semana Corte (Ciclo)',
            'Rendimiento Real (Kg/Ha)',
            'Pct_Cosecha_Semanal',
        ]
    )


t6_data = cargar_base_datos()

# 3. Formulario Lateral
st.sidebar.header('📝 Captura Cosecha Futura (2026+)')
with st.sidebar.form('form_cosecha_futura'):
  finca_f = st.text_input('Finca', value='CH')
  lote_f = st.text_input('Lote', value='CH01')
  veg_f = st.selectbox(
      'Vegetal / Referencia',
      [
          'Broccoli',
          'Ejote Fino',
          'Ejote Dulce',
          'Arveja China',
          'Esparrago',
          'Zanahoria',
      ],
  )
  area_f = st.number_input('Área (Ha)', min_value=0.1, value=1.0, step=0.1)
  cant_v_f = st.number_input('Cantidad V', min_value=1, value=1, step=1)
  ciclo_f = st.number_input('Ciclo', min_value=1, value=10, step=1)
  codigo_f = st.number_input('Código / Corte', min_value=1, value=1, step=1)
  ano_f = st.number_input(
      'Año', min_value=2025, max_value=2030, value=2026, step=1
  )
  semana_f = st.number_input(
      'Semana Calendario', min_value=1, max_value=52, value=10, step=1
  )
  sem_corte_f = st.number_input(
      'Semana Corte (Ciclo)', min_value=1, max_value=20, value=1, step=1
  )
  kilos_f = st.number_input('Kilos Cosechados', min_value=0.0, value=1000.0)

  guardar = st.form_submit_button('💾 Guardar Cosecha')

if guardar:
  area_ef = area_f / cant_v_f if cant_v_f > 0 else area_f
  rend_r = kilos_f / area_ef if area_ef > 0 else 0
  nuevo = pd.DataFrame([{
      'Finca': finca_f,
      'Lote': lote_f,
      'Area (Ha)': area_f,
      'Cantidad V': cant_v_f,
      'Area Efectiva (Ha)': area_ef,
      'Ciclo': ciclo_f,
      'Codigo': codigo_f,
      'Referencia': veg_f,
      'Kilos': kilos_f,
      'Semana Calendario': semana_f,
      'Ano': ano_f,
      'Semana Corte (Ciclo)': sem_corte_f,
      'Rendimiento Real (Kg/Ha)': rend_r,
      'Pct_Cosecha_Semanal': 0.0,
  }])
  t6_data = pd.concat([t6_data, nuevo], ignore_index=True)
  st.sidebar.success('✅ Registro guardado.')

# 4. Pestañas de Navegación
tab1, tab2, tab3 = st.tabs([
    '📊 Comportamiento Comparativo',
    '📈 Curvas Porcentuales',
    '🚀 Simulador de Pronósticos',
])

# -----------------------------------------------------------------------------
# TAB 1: COMPORTAMIENTO COMPARATIVO
# -----------------------------------------------------------------------------
with tab1:
  st.header('📊 Comportamiento Comparativo por Cultivo')

  if not t6_data.empty and 'Referencia' in t6_data.columns:
    lista_veg = sorted([
        v for v in t6_data['Referencia'].dropna().unique() if str(v).strip()
    ])
    if lista_veg:
      veg_sel = st.selectbox(
          'Selecciona Vegetal:', lista_veg, key='sb_tab1_veg'
      )
      t6_veg = t6_data[t6_data['Referencia'] == veg_sel].copy()

      def obtener_metricas(df_sub):
        if df_sub.empty:
          return 0, 0.0, 0.0
        cols_req = [
            'Finca',
            'Lote',
            'Ciclo',
            'Kilos',
            'Area Efectiva (Ha)',
            'Semana Corte (Ciclo)',
        ]
        if not all(c in df_sub.columns for c in cols_req):
          return 0, 0.0, 0.0

        ciclos = df_sub.groupby(['Finca', 'Lote', 'Ciclo']).agg(
            Kilos_Tot=('Kilos', 'sum'),
            Area_Ef=('Area Efectiva (Ha)', 'first'),
            Duracion=('Semana Corte (Ciclo)', 'max'),
        )
        ciclos['Rend'] = np.where(
            ciclos['Area_Ef'] > 0, ciclos['Kilos_Tot'] / ciclos['Area_Ef'], 0
        )
        return (
            len(ciclos),
            ciclos['Duracion'].mean() if not ciclos.empty else 0.0,
            ciclos['Rend'].mean() if not ciclos.empty else 0.0,
        )

      c_gen, d_gen, r_gen = obtener_metricas(t6_veg)
      c_hist, d_hist, r_hist = obtener_metricas(
          t6_veg[t6_veg['Ano'] < 2025] if 'Ano' in t6_veg.columns else pd.DataFrame()
      )
      c_act, d_act, r_act = obtener_metricas(
          t6_veg[t6_veg['Ano'] >= 2025] if 'Ano' in t6_veg.columns else pd.DataFrame()
      )

      df_resumen = pd.DataFrame([
          {
              'Periodo': 'Comportamiento General',
              'Ciclos Totales': c_gen,
              'Duración Promedio (Sem)': round(d_gen, 2),
              'Rendimiento Promedio (Kg/Ha)': round(r_gen, 1),
          },
          {
              'Periodo': 'Histórico (< 2025)',
              'Ciclos Totales': c_hist,
              'Duración Promedio (Sem)': round(d_hist, 2),
              'Rendimiento Promedio (Kg/Ha)': round(r_hist, 1),
          },
          {
              'Periodo': 'Actual (2025-2026+)',
              'Ciclos Totales': c_act,
              'Duración Promedio (Sem)': round(d_act, 2),
              'Rendimiento Promedio (Kg/Ha)': round(r_act, 1),
          },
      ])

      st.dataframe(df_resumen, use_container_width=True)

      fig_b = px.bar(
          df_resumen,
          x='Periodo',
          y='Rendimiento Promedio (Kg/Ha)',
          color='Periodo',
          text_auto='.1f',
          title=f'Rendimiento Promedio - {veg_sel}',
      )
      st.plotly_chart(fig_b, use_container_width=True)
  else:
    st.warning(
        'No se encontraron datos válidos en el archivo Excel cargado.'
    )

# -----------------------------------------------------------------------------
# TAB 2: CURVAS DE DISTRIBUCIÓN PORCENTUAL
# -----------------------------------------------------------------------------
with tab2:
  st.header('📈 Curvas Porcentuales de Producción Semanal')

  if not t6_data.empty and 'Referencia' in t6_data.columns:
    veg_sel2 = st.selectbox(
        'Selecciona Vegetal para Curvas:', lista_veg, key='sb_tab2_veg'
    )
    t6_v2 = t6_data[t6_data['Referencia'] == veg_sel2].copy()

    def get_curva(df_sub):
      if (
          df_sub.empty
          or 'Semana Corte (Ciclo)' not in df_sub.columns
          or 'Pct_Cosecha_Semanal' not in df_sub.columns
      ):
        return pd.DataFrame(columns=['Semana Corte (Ciclo)', 'Pct'])
      res = (
          df_sub.groupby('Semana Corte (Ciclo)')['Pct_Cosecha_Semanal']
          .mean()
          .reset_index()
      )
      res.columns = ['Semana Corte (Ciclo)', 'Pct']
      return res

    cg = get_curva(t6_v2)
    ch = get_curva(
        t6_v2[t6_v2['Ano'] < 2025] if 'Ano' in t6_v2.columns else pd.DataFrame()
    )
    ca = get_curva(
        t6_v2[t6_v2['Ano'] >= 2025] if 'Ano' in t6_v2.columns else pd.DataFrame()
    )

    fig_c = go.Figure()
    if not cg.empty:
      fig_c.add_trace(
          go.Scatter(
              x=cg['Semana Corte (Ciclo)'],
              y=cg['Pct'],
              mode='lines+markers',
              name='General',
          )
      )
    if not ch.empty:
      fig_c.add_trace(
          go.Scatter(
              x=ch['Semana Corte (Ciclo)'],
              y=ch['Pct'],
              mode='lines+markers',
              name='< 2025',
              line=dict(dash='dash'),
          )
      )
    if not ca.empty:
      fig_c.add_trace(
          go.Scatter(
              x=ca['Semana Corte (Ciclo)'],
              y=ca['Pct'],
              mode='lines+markers',
              name='2025-2026+',
          )
      )

    fig_c.update_layout(
        title=f'Distribución Semanal - {veg_sel2}',
        xaxis_title='Semana Relativa de Corte',
        yaxis_title='% Cosechado',
    )
    st.plotly_chart(fig_c, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: SIMULADOR
# -----------------------------------------------------------------------------
with tab3:
  st.header('🚀 Simulador de Pronósticos Futuros')

  if not t6_data.empty and 'Referencia' in t6_data.columns:
    c1, c2, c3 = st.columns(3)
    v_sim = c1.selectbox('Vegetal:', lista_veg, key='sb_sim')
    a_sim = c2.number_input('Área (Ha):', min_value=0.1, value=5.0)
    mod_sim = c3.radio(
        'Modelo:',
        ['Comportamiento Actual (2025-2026)', 'Histórico (<2025)', 'General'],
    )

    if st.button('🎯 Calcular Proyección'):
      sub_s = t6_data[t6_data['Referencia'] == v_sim]

      if mod_sim == 'Comportamiento Actual (2025-2026)':
        sub_s = sub_s[sub_s['Ano'] >= 2025]
      elif mod_sim == 'Histórico (<2025)':
        sub_s = sub_s[sub_s['Ano'] < 2025]

      if sub_s.empty:
        sub_s = t6_data[t6_data['Referencia'] == v_sim]

      if not sub_s.empty and 'Pct_Cosecha_Semanal' in sub_s.columns:
        curva_sim = (
            sub_s.groupby('Semana Corte (Ciclo)')['Pct_Cosecha_Semanal']
            .mean()
            .reset_index()
        )
        suma_pct = curva_sim['Pct_Cosecha_Semanal'].sum()
        curva_sim['Factor'] = (
            curva_sim['Pct_Cosecha_Semanal'] / suma_pct if suma_pct > 0 else 0
        )

        ciclos_s = sub_s.groupby(['Finca', 'Lote', 'Ciclo']).agg(
            K=('Kilos', 'sum'), A=('Area Efectiva (Ha)', 'first')
        )
        rend_prom = (
            (ciclos_s['K'] / ciclos_s['A']).mean() if not ciclos_s.empty else 0
        )

        kilos_est = a_sim * rend_prom
        curva_sim['Kilos Proyectados'] = curva_sim['Factor'] * kilos_est

        st.success(
            f'Estimación Total para {a_sim} Ha de {v_sim}:'
            f' **{kilos_est:,.1f} Kg**'
        )

        fig_sim_b = px.bar(
            curva_sim,
            x='Semana Corte (Ciclo)',
            y='Kilos Proyectados',
            text_auto='.1f',
            title=f'Proyección Semanal - {v_sim}',
        )
        st.plotly_chart(fig_sim_b, use_container_width=True)
        st.dataframe(curva_sim, use_container_width=True)
