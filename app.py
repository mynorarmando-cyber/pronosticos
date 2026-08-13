import os
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# 1. Configuración de la aplicación
st.set_page_config(
    page_title="CropPlanner - Plataforma Agrícola Integral",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("🌾 CropPlanner: Análisis Comparativo y Simulador Agrícola")
st.markdown("Módulo de diagnóstico comparativo de curvas de producción e ingesta continua de nuevos datos real-time.")

# 2. Carga Segura y Automatizada de Archivos Existentes
@st.cache_data
def cargar_matriz_recomendada():
    archivo_matriz = 'Matris recomendada.xlsx'
    
    if not os.path.exists(archivo_matriz):
        st.error(f"❌ No se encontró el archivo '{archivo_matriz}' en el directorio raíz.")
        return pd.DataFrame(), pd.DataFrame()
    
    # 2.1 Carga Hoja 'comportamiento ' (Rendimientos y Ciclos)
    df_comp_raw = pd.read_excel(archivo_matriz, sheet_name='comportamiento ', skiprows=1)
    df_comp = df_comp_raw.copy()
    df_comp.columns = [str(c).strip() for c in df_comp.iloc[0].values]
    df_comp = df_comp.iloc[1:].reset_index(drop=True)
    
    # Limpieza de nombres de columna
    df_comp = df_comp.rename(columns={
        'Vegetal (Referencia)': 'Vegetal',
        'Periodo': 'Periodo',
        'Ciclos Totales': 'Ciclos Totales',
        'Duracion Promedio Real (Semanas)': 'Duracion_Promedio',
        'Rendimiento Promedio (Kg/Ha)': 'Rendimiento_Promedio',
        'Rendimiento Mediana (Kg/Ha)': 'Rendimiento_Mediana'
    })
    
    for col in ['Ciclos Totales', 'Duracion_Promedio', 'Rendimiento_Promedio', 'Rendimiento_Mediana']:
        if col in df_comp.columns:
            df_comp[col] = pd.to_numeric(df_comp[col], errors='coerce')

    # 2.2 Carga Hoja 'Modelo de pronosticos' (Curvas Porcentuales Semanales)
    df_curvas_raw = pd.read_excel(archivo_matriz, sheet_name='Modelo de pronosticos', skiprows=0)
    df_curvas = df_curvas_raw.copy()
    df_curvas.columns = [str(c).strip() for c in df_curvas.iloc[0].values]
    df_curvas = df_curvas.iloc[1:].reset_index(drop=True)
    
    # Renombrar columna principal
    col_veg = df_curvas.columns[0]
    df_curvas = df_curvas.rename(columns={col_veg: 'Vegetal'})
    
    # Seleccionar columnas de semana 1 a 7
    cols_semanas = [c for c in df_curvas.columns if 'Semana' in str(c) and 'Total' not in str(c)]
    for c in cols_semanas:
        df_curvas[c] = pd.to_numeric(df_curvas[c], errors='coerce').fillna(0)
        
    return df_comp, df_curvas

df_comp, df_curvas = cargar_matriz_recomendada()

# Inicializar sesión para guardar cosechas dinámicas
if 'cosechas_nuevas' not in st.session_state:
    st.session_state.cosechas_nuevas = pd.DataFrame()

# 3. Formulario Lateral para Ingesta Continua (2026+)
st.sidebar.header("📝 Captura Cosecha Futura (2026+)")
with st.sidebar.form("form_cosecha_futura"):
    st.markdown("**Agregar Nuevo Corte Real**")
    finca_f = st.text_input("Finca", value="CH")
    lote_f = st.text_input("Lote", value="CH01")
    veg_f = st.selectbox("Vegetal / Referencia", ["Broccoli", "Fino", "Dulce", "China", "Esparrago", "Grano", "Zanahoria", "Runner"])
    area_f = st.number_input("Área (Ha)", min_value=0.1, value=1.0, step=0.1)
    cant_v_f = st.number_input("Cantidad V", min_value=1, value=1, step=1)
    ciclo_f = st.number_input("Ciclo", min_value=1, value=10, step=1)
    codigo_f = st.number_input("Código / Corte", min_value=1, value=1, step=1)
    ano_f = st.number_input("Año", min_value=2025, max_value=2030, value=2026, step=1)
    semana_f = st.number_input("Semana Calendario (1-52)", min_value=1, max_value=52, value=10, step=1)
    sem_corte_f = st.number_input("Semana Corte (Ciclo)", min_value=1, max_value=20, value=1, step=1)
    kilos_f = st.number_input("Kilos Cosechados", min_value=0.0, value=1000.0)
    
    guardar = st.form_submit_button("💾 Guardar Cosecha")

if guardar:
    area_efectiva = area_f / cant_v_f if cant_v_f > 0 else area_f
    rend_real = kilos_f / area_efectiva if area_efectiva > 0 else 0
    nuevo_reg = pd.DataFrame([{
        'Finca': finca_f,
        'Lote': lote_f,
        'Area_Ha': area_f,
        'Ciclo': ciclo_f,
        'Vegetal': veg_f,
        'Kilos': kilos_f,
        'Semana_Calendario': semana_f,
        'Ano': ano_f,
        'Semana_Corte': sem_corte_f,
        'Rendimiento_KgHa': rend_real
    }])
    st.session_state.cosechas_nuevas = pd.concat([st.session_state.cosechas_nuevas, nuevo_reg], ignore_index=True)
    st.sidebar.success("✅ Registro guardado con éxito en sesión.")

# 4. Navegación Principal por Pestañas
tab1, tab2, tab3 = st.tabs([
    "📊 Comportamiento Comparativo por Cultivo",
    "📈 Curvas Porcentuales de Producción",
    "🚀 Simulador de Pronósticos Futuros"
])

# -----------------------------------------------------------------------------
# TAB 1: COMPORTAMIENTO COMPARATIVO
# -----------------------------------------------------------------------------
with tab1:
    st.header("📊 Comportamiento Comparativo y Duración Real por Cultivo")
    
    if not df_comp.empty and 'Vegetal' in df_comp.columns:
        lista_vegetales = sorted([v for v in df_comp['Vegetal'].dropna().unique() if str(v).strip()])
        veg_sel = st.selectbox("Selecciona Vegetal para Inspeccionar:", lista_vegetales)
        
        df_v = df_comp[df_comp['Vegetal'] == veg_sel].copy()
        
        # Incorporar registros dinámicos si aplican
        if not st.session_state.cosechas_nuevas.empty:
            nuevos_v = st.session_state.cosechas_nuevas[st.session_state.cosechas_nuevas['Vegetal'] == veg_sel]
            if not nuevos_v.empty:
                rend_nuevos = nuevos_v['Rendimiento_KgHa'].mean()
                ciclos_nuevos = len(nuevos_v['Ciclo'].unique())
                duracion_nuevos = nuevos_v['Semana_Corte'].max()
                
                filas_nuevas = pd.DataFrame([{
                    'Vegetal': veg_sel,
                    'Periodo': 'Ingresado Recientemente (2026)',
                    'Ciclos Totales': ciclos_nuevos,
                    'Duracion_Promedio': duracion_nuevos,
                    'Rendimiento_Promedio': rend_nuevos,
                    'Rendimiento_Mediana': rend_nuevos
                }])
                df_v = pd.concat([df_v, filas_nuevas], ignore_index=True)

        st.subheader(f"📋 Resumen de Desempeño: {veg_sel}")
        st.dataframe(df_v[['Periodo', 'Ciclos Totales', 'Duracion_Promedio', 'Rendimiento_Promedio', 'Rendimiento_Mediana']], use_container_width=True)
        
        fig_b = px.bar(
            df_v,
            x='Periodo',
            y='Rendimiento_Promedio',
            color='Periodo',
            text_auto='.1f',
            title=f'Rendimiento Promedio (Kg/Ha) - {veg_sel}',
            color_discrete_sequence=['#2E8B57', '#4682B4', '#E67E22', '#9B59B6']
        )
        st.plotly_chart(fig_b, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 2: CURVAS DE DISTRIBUCIÓN PORCENTUAL
# -----------------------------------------------------------------------------
with tab2:
    st.header("📈 Curvas de Distribución Porcentual Promedio (% por Semana de Cosecha)")
    
    if not df_curvas.empty and 'Vegetal' in df_curvas.columns:
        lista_veg_curvas = sorted([v for v in df_curvas['Vegetal'].dropna().unique() if str(v).strip()])
        veg_curva_sel = st.selectbox("Selecciona Vegetal para Analizar Curva:", lista_veg_curvas)
        
        row_c = df_curvas[df_curvas['Vegetal'] == veg_curva_sel]
        
        if not row_c.empty:
            cols_sem = [c for c in row_c.columns if 'Semana' in str(c) and 'Total' not in str(c)]
            
            valores_pct = row_c[cols_sem].values[0]
            # Convertir a porcentajes (0 a 100%)
            valores_pct_100 = [v * 100 if v <= 1.0 else v for v in valores_pct]
            
            df_curva_plot = pd.DataFrame({
                'Semana Relativa': cols_sem,
                '% Cosechado': valores_pct_100
            })
            
            fig_c = px.line(
                df_curva_plot,
                x='Semana Relativa',
                y='% Cosechado',
                markers=True,
                title=f'Distribución Semanal de Cosecha - {veg_curva_sel}',
                text=[f"{v:.1f}%" for v in valores_pct_100]
            )
            fig_c.update_traces(textposition="top center", line=dict(color='#2E8B57', width=3))
            st.plotly_chart(fig_c, use_container_width=True)
            
            st.dataframe(df_curva_plot.T, use_container_width=True)

# -----------------------------------------------------------------------------
# TAB 3: SIMULADOR DE PRONÓSTICOS
# -----------------------------------------------------------------------------
with tab3:
    st.header("🚀 Simulador de Pronósticos Futuros")
    
    if not df_comp.empty and not df_curvas.empty:
        col_s1, col_s2, col_s3 = st.columns(3)
        veg_sim = col_s1.selectbox("Vegetal a Planificar:", lista_vegetales, key="sim_v")
        area_sim = col_s2.number_input("Área a Sembrar (Hectáreas):", min_value=0.1, max_value=500.0, value=5.0)
        modelo_sim = col_s3.radio("Base de Rendimiento:", ["Actual (2025-2026)", "Historico (<2025)"])
        
        if st.button("🎯 Calcular Proyección Cosecha"):
            # Obtener Rendimiento Base
            sub_comp = df_comp[(df_comp['Vegetal'] == veg_sim) & (df_comp['Periodo'].str.contains(modelo_sim, case=False, na=False))]
            
            if sub_comp.empty:
                sub_comp = df_comp[df_comp['Vegetal'] == veg_sim]
                
            rend_base = sub_comp['Rendimiento_Promedio'].values[0] if not sub_comp.empty else 5000.0
            kilos_totales_est = area_sim * rend_base
            
            # Obtener Curva Porcentual
            row_curva = df_curvas[df_curvas['Vegetal'] == veg_sim]
            if row_curva.empty:
                # Búsqueda por coincidencia parcial si Extrafino/Fino
                row_curva = df_curvas[df_curvas['Vegetal'].str.contains(veg_sim, case=False, na=False)]
            
            if not row_curva.empty:
                cols_sem = [c for c in row_curva.columns if 'Semana' in str(c) and 'Total' not in str(c)]
                pcts = row_curva[cols_sem].values[0]
                pcts_norm = [p if p <= 1.0 else p/100.0 for p in pcts]
                
                df_sim_res = pd.DataFrame({
                    'Semana Relativa': cols_sem,
                    '% Distribución': [p * 100 for p in pcts_norm],
                    'Kilos Proyectados': [p * kilos_totales_est for p in pcts_norm]
                })
                
                # Filtrar semanas con producción > 0
                df_sim_res = df_sim_res[df_sim_res['Kilos Proyectados'] > 0]
                
                st.success(f" Proyección Total Estimada para **{area_sim} Ha** de **{veg_sim}** ({modelo_sim}): **{kilos_totales_est:,.1f} Kg**")
                
                fig_sim = px.bar(
                    df_sim_res,
                    x='Semana Relativa',
                    y='Kilos Proyectados',
                    text_auto='.1f',
                    title=f'Estimación Semanal de Cosecha ({veg_sim})',
                    color_discrete_sequence=['#2E8B57']
                )
                st.plotly_chart(fig_sim, use_container_width=True)
                
                st.dataframe(df_sim_res, use_container_width=True)
            else:
                st.warning(f"No se encontró una curva de distribución registrada para el cultivo: {veg_sim}")
