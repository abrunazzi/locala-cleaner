import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# Configurazione pagina
st.set_page_config(page_title="Locala Data Cleaner", page_icon="🚀")

st.title("🚀 Locala Report Transformer")
st.markdown("Trascina il file Excel e scarica il dataset pulito.")

# 1. CARICAMENTO (Interfaccia Streamlit)
uploaded_file = st.file_uploader("Carica il Datasetton (Excel o CSV)", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # 2. LETTURA
        if uploaded_file.name.endswith('.xlsx'):
            df_raw = pd.read_excel(uploaded_file)
        else:
            df_raw = pd.read_csv(uploaded_file, sep=None, engine='python')

        # 3. LOGICA DI PULIZIA (Il tuo codice originale)
        df_raw = df_raw.dropna(how='all', axis=1)
        col_id = df_raw.columns[0]
        df_raw = df_raw.rename(columns={col_id: 'Codice_Impianto'})
        
        tutte_le_colonne = df_raw.columns.tolist()
        mappa_colonne_date = {}
        data_corrente = None

        for col in tutte_le_colonne:
            col_str = str(col).strip()
            match_data = re.search(r'(\d{2}/\d{2}/\d{2,4})', col_str)
            match_iso = re.search(r'(\d{4}-\d{2}-\d{2})', col_str)
            contiene_orario = ":" in col_str
            
            if (match_data or match_iso) and not contiene_orario:
                if match_data:
                    data_corrente = match_data.group(1)
                else:
                    data_corrente = datetime.strptime(match_iso.group(1), '%Y-%m-%d').strftime('%d/%m/%y')
            
            if data_corrente:
                mappa_colonne_date[col] = data_corrente

        df_long = df_raw.melt(id_vars=['Codice_Impianto'], var_name='Attributo', value_name='Valore')
        df_long['Data'] = df_long['Attributo'].map(mappa_colonne_date)
        
        def pulisci_orario(val):
            s = str(val).lower()
            match_ora = re.search(r'(\d{1,2}:\d{2})', s)
            if match_ora:
                if "-" in s: return "RANGE"
                return match_ora.group(1)
            return "NON_ORA"

        df_long['Orario_Clean'] = df_long['Attributo'].apply(pulisci_orario)
        df_finale = df_long[(df_long['Orario_Clean'] != "RANGE") & (df_long['Orario_Clean'] != "NON_ORA") & (df_long['Data'].notna())].copy()

        if not df_finale.empty:
            df_finale['Valore'] = pd.to_numeric(df_finale['Valore'].astype(str).str.replace(',', '.'), errors='coerce')
            df_finale = df_finale.dropna(subset=['Codice_Impianto', 'Valore'])
            df_finale = df_finale.rename(columns={'Orario_Clean': 'Orario'})
            df_finale = df_finale[['Codice_Impianto', 'Data', 'Orario', 'Valore']].sort_values(by=['Codice_Impianto', 'Data', 'Orario'])

            # 4. DOWNLOAD DEL RISULTATO
            st.success(f"✅ HA FUNZIONATO! Estratti {len(df_finale)} record.")
            
            # Prepariamo il CSV per il download
            csv_buffer = io.StringIO()
            df_finale.to_csv(csv_buffer, index=False, sep=';', decimal=',')
            
            st.download_button(
                label="📥 SCARICA IL DATSETTINO",
                data=csv_buffer.getvalue(),
                file_name="Datasettino_Pulito.csv",
                mime="text/csv"
            )
        else:
            st.error("Nessun orario rilevato.")

    except Exception as e:
        st.error(f"Si è verificato un errore: {e}")