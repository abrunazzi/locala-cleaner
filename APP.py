import streamlit as st
import pandas as pd
import io
import re
from datetime import datetime

# Configurazione pagina
st.set_page_config(page_title="Locala Data Cleaner", page_icon=" 🦆 ")

st.title("Collasso di Dataset Locala")
st.markdown("Carica i file necessari e clicca su **Avvia Elaborazione**.")

# --- 1. CARICAMENTO FILE ---
col1, col2 = st.columns(2)

with col1:
    uploaded_file = st.file_uploader("1. Datasettone VIOOH (Obbligatorio)", type=['xlsx', 'csv'])

with col2:
    details_file = st.file_uploader("2. Dettagli Impianti (Facoltativo)", type=['xlsx', 'csv'])

# --- 2. BOTTONE DI INVIO ---
# Il bottone compare solo se almeno il primo file è stato caricato
if uploaded_file:
    if st.button("🦆 AVVIA ELABORAZIONE", use_container_width=True):
        try:
            with st.spinner('🦆 In corso...'):
                # --- 3. LETTURA DATASET PRINCIPALE ---
                if uploaded_file.name.endswith('.xlsx'):
                    df_raw = pd.read_excel(uploaded_file)
                else:
                    df_raw = pd.read_csv(uploaded_file, sep=None, engine='python')

                # --- 4. LOGICA DI PULIZIA E UNPIVOT ---
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
                    
                    # --- 5. AGGIUNTA COORDINATE (Se presente il secondo file) ---
                    if details_file:
                        if details_file.name.endswith('.xlsx'):
                            df_details = pd.read_excel(details_file)
                        else:
                            df_details = pd.read_csv(details_file, sep=None, engine='python')
                        
                        # Normalizzazione colonne dettagli
                        col_id_details = df_details.columns[0]
                        df_details = df_details.rename(columns={col_id_details: 'Codice_Impianto'})
                        # Cerchiamo Lat e Long ignorando maiuscole/minuscole
                        df_details.columns = [c.capitalize() if c.lower() in ['lat', 'long'] else c for c in df_details.columns]
                        
                        if 'Lat' in df_details.columns and 'Long' in df_details.columns:
                            df_subset = df_details[['Codice_Impianto', 'Lat', 'Long']]
                            # Join left: teniamo tutti i dati originali e aggiungiamo le coordinate dove possibile
                            df_finale = pd.merge(df_finale, df_subset, on='Codice_Impianto', how='left')
                            st.info(" Coordinate geografiche integrate correttamente.")
                        else:
                            st.warning(" Colonne 'Lat' o 'Long' non trovate nel file dettagli.")

                    # Selezione finale colonne
                    cols_to_keep = ['Codice_Impianto', 'Data', 'Orario', 'Valore']
                    if 'Lat' in df_finale.columns: 
                        cols_to_keep.extend(['Lat', 'Long'])
                    
                    df_finale = df_finale[cols_to_keep].sort_values(by=['Codice_Impianto', 'Data', 'Orario'])

                    # --- 6. RISULTATO E DOWNLOAD ---
                    st.success(f" Elaborazione completata! Estratti {len(df_finale)} record.")
                    
                    csv_buffer = io.StringIO()
                    df_finale.to_csv(csv_buffer, index=False, sep=';', decimal=',')
                    
                    st.download_button(
                        label=" SCARICA IL FILE CSV",
                        data=csv_buffer.getvalue(),
                        file_name="Dataset_Locala_Pulito.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                else:
                    st.error("Nessun dato orario valido trovato nel file.")

        except Exception as e:
            st.error(f"Si è verificato un errore critico: {e}")
else:
    st.info("In attesa del file principale per iniziare...")
