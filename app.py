import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np

# Configuración de la página
st.set_page_config(page_title="CropPlanner Pro - Modelo Gerencial", layout="wide")

st.title("🌾 CropPlanner: Modelo Analítico de Rendimiento y Pronóstico")
st.markdown("Análisis avanzado de curvas de producción, rendimiento por hectárea y control de ciclos limpios.")

@st.cache_data
def cargar_y_limpiar_datos():
    # Cargar archivo Excel
    file_path = 'Analisis final.xlsx'
    df_raw = pd.read_excel(file_path, sheet_name=0)
    
    # Extraer Tabla 6 (Datos base de cosecha)
    df_base = df_raw.iloc[1:, 1:14].copy()
    df_base.columns = ['Finca', 'Lote', 'Area', 'Ciclo', 'Codigo', 'Vegetal', 'Referencia', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio', 'Mes']
    
    # Conversión numérica de columnas clave
    cols_num = ['Area', 'Ciclo', 'Codigo', 'Cantidad_V', 'Dur_SC', 'Kilos', 'Semana', 'Anio']
    for col in cols_num:
        df_base[col] = pd.to_numeric(df_base[col], errors='coerce')
        
    df_base = df_base.dropna(subset=['Vegetal', 'Kilos', 'Ciclo', 'Anio'])
    df_base['Periodo'] = df_base['Anio'].apply(lambda x: 'Actual (2025-2026)' if x >= 2025 else 'Histórico (<2025)')
    
    # 1. Calcular duración real de cada ciclo (número de semanas de cosecha)
    dur_ciclo = df_base.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo'], as_index=False)['Semana'].nunique()
    dur_ciclo.rename(columns={'Semana': 'Duracion_Real'}, inplace=True)
    
    # 2. Filtrado inteligente de Outliers (Elimina ciclos anormalmente largos/cortos como el caso raro de 11 semanas)
    valid_cycles = []
    for (veg, per), group in dur_ciclo.groupby(['Vegetal', 'Periodo']):
        q1 = group['Duracion_Real'].quantile(0.25)
        q3 = group['Duracion_Real'].quantile(0.75)
        iqr = q3 - q1
        limite_superior = q3 + 1.5 * iqr
        if iqr == 0:
            limite_superior = group['Duracion_Real'].max()
        
        # Filtramos para quedarnos con el comportamiento regular/esperado
        filtered_group = group[group['Duracion_Real'] <= limite_superior]
        valid_cycles.append(filtered_group)
        
    ciclos_limpios = pd.concat(valid_cycles, ignore_index=True)
    
    # 3. Cruzar con la tabla base para aislar sólo los ciclos limpios
    df_limpio = df_base.merge(
        ciclos_limpios[['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']], 
        on=['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']
    )
    
    # 4. Calcular la semana relativa de cosecha (1, 2, 3...) y el porcentaje aportado al ciclo
    df_limpio = df_limpio.sort_values(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo', 'Codigo'])
    df_limpio['Semana_Rel'] = df_limpio.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo']).cumcount() + 1
    
    tot_ciclo = df_limpio.groupby(['Vegetal', 'Periodo', 'Finca', 'Lote', 'Ciclo'])['Kilos'].transform('sum')
    df_limpio['Pct_Semanal'] = (df_limpio['Kilos'] / tot_ciclo) * 100
    
    return df_limpio

# Cargar dataset procesado
df_data = cargar_y_limpiar_datos()

# --- BARRA LATERAL: FILTROS MULTI-SELECCIÓN ---
st.sidebar.header("Filtros del Modelo")
vegetales_disponibles = sorted(df_data['Vegetal'].dropna().unique())
sel_vegetales = st.sidebar.multiselect("Seleccionar Vegetal(es):", vegetales_disponibles, default=[vegetales_disponibles[0]])

periodos_disponibles = sorted(df_data['Periodo'].unique())
sel_periodos = st.sidebar.multiselect("Seleccionar Periodo(s):", periodos_disponibles, default=periodos_disponibles)

# Filtrar datos según la selección del usuario
df_filtrado = df_data[(df_data['Vegetal'].isin(sel_vegetales)) & (df_data['Periodo'].isin(sel_periodos))]

# --- CUERPO PRINCIPAL ---
tab1, tab2, tab3 = st.tabs(["📊 Curva de Producción (%)", "🎯 Rendimiento Real (Kilos/Ha)", "🔮 Simulador de Proyección"])

with tab1:
    st.subheader("Curva de Producción Porcentual (Limpia de Outliers)")
    st.markdown("Muestra qué porcentaje del volumen total se cosecha en cada semana relativa del ciclo (Semana 1, 2, 3...), promediando únicamente los ciclos con duración normalizada.")
    
    if not df_filtrado.empty:
        # Matriz pivoteada de porcentajes
        matriz_pct = df_filtrado.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().unstack(fill_value=0)
        st.dataframe(matriz_pct.style.format("{:.2f}%"), use_container_width=True)
        
        # Gráfica de líneas interactiva
        fig = px.line(
            df_filtrado.groupby(['Vegetal', 'Periodo', 'Semana_Rel'])['Pct_Semanal'].mean().reset_index(),
            x='Semana_Rel', y='Pct_Semanal', color='Periodo', facet_col='Vegetal', facet_col_wrap=2,
            markers=True, title="Tendencia de Curvas por Vegetal (% de Cosecha Semanal)"
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Por favor selecciona al menos un vegetal y un periodo en la barra lateral.")

with tab2:
    st.subheader("Historial de Rendimiento en Kilos")
    st.markdown("Comportamiento del volumen total cosechado por año y vegetal para evaluar fluctuaciones de época.")
    
    if not df_filtrado.empty:
        rend_resumen = df_filtrado.groupby(['Vegetal', 'Anio', 'Periodo'])['Kilos'].sum().reset_index()
        fig_rend = px.bar(
            rend_resumen, x='Anio', y='Kilos', color='Vegetal', barmode='group',
            title="Producción Total Anual en Kilos"
        )
        st.plotly_chart(fig_rend, use_container_width=True)
        
        st.dataframe(rend_resumen.pivot_table(index=['Vegetal', 'Periodo'], columns='Anio', values='Kilos', fill_value=0), use_container_width=True)
    else:
        st.warning("Selecciona filtros válidos.")

with tab3:
    st.subheader("Simulador de Pronóstico a Futuro")
    st.markdown("Proyecta los kilos esperados semana a semana para una nueva siembra basándote en la curva actual limpia.")
    
    if len(sel_vegetales) == 1:
        veg_sel = sel_vegetales[0]
        col1, col2 = st.columns(2)
        with col1:
            kilos_estimados = st.number_input("Kilos Totales Esperados para el Lote:", min_value=100.0, value=5000.0, step=100.0)
        with col2:
            periodo_base = st.selectbox("Usar Curva de Periodo:", ['Actual (2025-2026)', 'Histórico (<2025)'])
            
        # Extraer la curva porcentual promedio del vegetal y periodo seleccionados
        sub_df = df_filtrado[(df_filtrado['Vegetal'] == veg_sel) & (df_filtrado['Periodo'] == periodo_base)]
        if not sub_df.empty:
            curva_proyectada = sub_df.groupby('Semana_Rel')['Pct_Semanal'].mean().reset_index()
            curva_proyectada['Kilos_Proyectados'] = (curva_proyectada['Pct_Semanal'] / 100.0) * kilos_estimados
            
            st.markdown(f"### Pronóstico de Cosecha Semanal para: **{veg_sel}**")
            st.dataframe(curva_proyectada.style.format({'Pct_Semanal': '{:.2f}%', 'Kilos_Proyectados': '{:,.2f} kg'}), use_container_width=True)
            
            fig_proj = px.bar(
                curva_proyectada, x='Semana_Rel', y='Kilos_Proyectados',
                text=curva_proyectada['Kilos_Proyectados'].apply(lambda x: f"{x:,.0f} kg"),
                title=f"Distribución de Kilos por Semana - {veg_sel}"
            )
            st.plotly_chart(fig_proj, use_container_width=True)
        else:
            st.info("No hay suficientes datos limpios para la combinación seleccionada en este simulador.")
    else:
        st.info("💡 **Tip para el Simulador:** Selecciona **exactamente un solo vegetal** en el filtro de la barra lateral para activar la proyección detallada semana a semana.")
