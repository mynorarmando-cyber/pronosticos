import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class AgronomicForecastEngine:
    def __init__(self, file_path):
        self.file_path = file_path
        self.t6 = None
        self.t10 = None
        self.curvas_hist = None
        self.curvas_recientes = None
        self.estacionalidad = None
        self.rendimientos_base = None
        
        self._cargar_y_limpiar_datos()
        self._procesar_tabla_10()
        self._calcular_curvas_produccion()
        self._calcular_indices_estacionales()
        self._calcular_rendimientos_ponderados()

    def _cargar_y_limpiar_datos(self):
        xls = pd.ExcelFile(self.file_path)
        df_raw = pd.read_excel(xls, sheet_name=xls.sheet_names[0], skiprows=1)
        t6 = df_raw.iloc[:, 1:14].copy()
        t6.columns = ['Finca', 'Lote', 'Area', 'Ciclo', 'Codigo', 'Vegetal', 'Referencia', 
                      'Cantidad_V', 'Duracion_SC', 'Kilos', 'Semana', 'Ano', 'Mes']
        t6 = t6.dropna(subset=['Finca', 'Ciclo', 'Kilos'])

        for col in ['Area', 'Ciclo', 'Codigo', 'Cantidad_V', 'Duracion_SC', 'Kilos', 'Semana', 'Ano']:
            t6[col] = pd.to_numeric(t6[col], errors='coerce')

        t6['Area_Efectiva'] = t6['Area'] / t6['Cantidad_V']
        t6['Rendimiento_Semanal_KgHa'] = t6['Kilos'] / t6['Area_Efectiva']
        
        t6 = t6.sort_values(by=['Finca', 'Lote', 'Ciclo', 'Referencia', 'Codigo', 'Semana'])
        t6['Semana_Relativa'] = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia']).cumcount() + 1

        totales_ciclo = t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia'])['Kilos'].transform('sum')
        t6['Pct_Cosecha_Semanal'] = t6['Kilos'] / totales_ciclo

        def asignacion_peso_ano(ano):
            if ano >= 2024: return 0.50
            elif ano >= 2022: return 0.30
            else: return 0.20

        t6['Peso_Temporal'] = t6['Ano'].apply(asignacion_peso_ano)
        self.t6 = t6

    def _procesar_tabla_10(self):
        t10 = self.t6.groupby(['Finca', 'Lote', 'Ciclo', 'Referencia', 'Ano']).agg(
            Area=('Area', 'first'),
            Cantidad_V=('Cantidad_V', 'first'),
            Area_Efectiva=('Area_Efectiva', 'first'),
            Primera_Semana=('Semana', 'min'),
            Ultima_Semana=('Semana', 'max'),
            Duracion_Real=('Semana_Relativa', 'max'),
            Kilos_Totales=('Kilos', 'sum'),
            Peso_Temporal=('Peso_Temporal', 'first')
        ).reset_index()

        t10['Rendimiento_Real_KgHa'] = t10['Kilos_Totales'] / t10['Area_Efectiva']
        self.t10 = t10

    def _calcular_curvas_produccion(self):
        df_hist = self.t6[self.t6['Ano'] <= 2022]
        df_rec = self.t6[self.t6['Ano'] >= 2023]

        curvas_h = df_hist.groupby(['Referencia', 'Semana_Relativa'])['Pct_Cosecha_Semanal'].mean().reset_index()
        curvas_r = df_rec.groupby(['Referencia', 'Semana_Relativa'])['Pct_Cosecha_Semanal'].mean().reset_index()

        curvas_h['Pct_Normalizado'] = curvas_h.groupby('Referencia')['Pct_Cosecha_Semanal'].transform(lambda x: x / x.sum())
        curvas_r['Pct_Normalizado'] = curvas_r.groupby('Referencia')['Pct_Cosecha_Semanal'].transform(lambda x: x / x.sum())

        self.curvas_hist = curvas_h
        self.curvas_recientes = curvas_r

    def _calcular_indices_estacionales(self):
        rend_global = (self.t6['Rendimiento_Semanal_KgHa'] * self.t6['Peso_Temporal']).sum() / self.t6['Peso_Temporal'].sum()

        def prom_ponderado(g):
            return (g['Rendimiento_Semanal_KgHa'] * g['Peso_Temporal']).sum() / g['Peso_Temporal'].sum()

        est = self.t6.groupby(['Referencia', 'Semana']).apply(prom_ponderado).reset_index(name='Rendimiento_Ponderado')
        rend_global_veg = self.t6.groupby('Referencia').apply(prom_ponderado).to_dict()

        est['Indice_Estacional'] = est.apply(
            lambda r: r['Rendimiento_Ponderado'] / rend_global_veg.get(r['Referencia'], rend_global), axis=1
        )
        self.estacionalidad = est

    def _calcular_rendimientos_ponderados(self):
        def calc_percentiles(g):
            vals = g['Rendimiento_Real_KgHa']
            return pd.Series({
                'P25_Conservador': np.percentile(vals, 25),
                'P50_Probable': np.percentile(vals, 50),
                'P75_Optimista': np.percentile(vals, 75)
            })

        self.rendimientos_base = self.t10.groupby('Referencia').apply(calc_percentiles).reset_index()

    def generar_pronostico(self, vegetal, area_ha, fecha_siembra_str):
        fecha_siembra = datetime.strptime(fecha_siembra_str, "%Y-%m-%d")
        fecha_inicio_cosecha = fecha_siembra + timedelta(days=60)
        semana_inicio = fecha_inicio_cosecha.isocalendar()[1]

        curva_veg = self.curvas_recientes[self.curvas_recientes['Referencia'] == vegetal].copy()
        if curva_veg.empty:
            curva_veg = self.curvas_hist[self.curvas_hist['Referencia'] == vegetal].copy()

        rend_base = self.rendimientos_base[self.rendimientos_base['Referencia'] == vegetal]
        if rend_base.empty:
            return None, None

        p25 = rend_base['P25_Conservador'].values[0]
        p50 = rend_base['P50_Probable'].values[0]
        p75 = rend_base['P75_Optimista'].values[0]

        proyecciones = []
        for idx, row in curva_veg.iterrows():
            sem_rel = int(row['Semana_Relativa'])
            pct = row['Pct_Normalizado']
            sem_cal = (semana_inicio + sem_rel - 1) % 52
            if sem_cal == 0: sem_cal = 52

            idx_est = self.estacionalidad[(self.estacionalidad['Referencia'] == vegetal) & (self.estacionalidad['Semana'] == sem_cal)]
            factor_est = idx_est['Indice_Estacional'].values[0] if not idx_est.empty else 1.0

            kilos_conservador = area_ha * p25 * factor_est * pct
            kilos_probable = area_ha * p50 * factor_est * pct
            kilos_optimista = area_ha * p75 * factor_est * pct

            proyecciones.append({
                'Semana_Relativa': sem_rel,
                'Semana_Calendario': sem_cal,
                'Pct_Curva': round(pct * 100, 2),
                'Factor_Estacional': round(factor_est, 2),
                'Kilos_Conservador': round(kilos_conservador, 1),
                'Kilos_Probable': round(kilos_probable, 1),
                'Kilos_Optimista': round(kilos_optimista, 1)
            })

        df_res = pd.DataFrame(proyecciones)
        totales = {
            'Vegetal': vegetal,
            'Area_Ha': area_ha,
            'Fecha_Siembra': fecha_siembra_str,
            'Fecha_Est_Cosecha': fecha_inicio_cosecha.strftime("%Y-%m-%d"),
            'Duracion_Semanas': len(df_res),
            'Total_Conservador_Kg': round(df_res['Kilos_Conservador'].sum(), 1),
            'Total_Probable_Kg': round(df_res['Kilos_Probable'].sum(), 1),
            'Total_Optimista_Kg': round(df_res['Kilos_Optimista'].sum(), 1)
        }
        return totales, df_res