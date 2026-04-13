import streamlit as st
import pandas as pd
import io
import os
from datetime import datetime

# 1. Configuration de la page et Style
st.set_page_config(page_title="Gestion Fournisseurs Cloud", layout="wide", page_icon="☁️")

# CSS pour un look professionnel (Style moderne)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Inter', sans-serif; }
    .main-header { color: #1E3A8A; border-bottom: 3px solid #3B82F6; padding-bottom: 10px; margin-bottom: 25px; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #3B82F6; color: white; border: none; padding: 10px; }
    .stTab { background-color: #f8fafc; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Gestion des données (Système de stockage persistant)
DB_FILE = "suppliers_database_v2.csv"

def load_data():
    if "db" not in st.session_state:
        if os.path.exists(DB_FILE):
            try:
                st.session_state.db = pd.read_csv(DB_FILE)
            except:
                st.session_state.db = pd.DataFrame(columns=["Nom", "Catégories", "Contact", "Adresse"])
        else:
            st.session_state.db = pd.DataFrame(columns=["Nom", "Catégories", "Contact", "Adresse"])
    return st.session_state.db

def save_data(df):
    st.session_state.db = df
    df.to_csv(DB_FILE, index=False)

# 3. Traitement des données (Correction d'erreurs Type/Float)
def safe_text(val):
    """Convertit les valeurs en texte pour éviter l'erreur (float found)"""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def process_excel_robust(file, selected_sheets):
    extracted_data = []
    for sheet in selected_sheets:
        try:
            # Lecture immédiate en tant que texte pour éviter les conflits
            df = pd.read_excel(file, sheet_name=sheet).fillna("").astype(str)
            
            cols = df.columns.tolist()
            for _, row in df.iterrows():
                name = safe_text(row[cols[0]])
                if name and len(name) > 1:
                    extracted_data.append({
                        "Nom": name,
                        "Catégories": safe_text(sheet),
                        "Contact": safe_text(row[cols[1]]) if len(cols) > 1 else "",
                        "Adresse": safe_text(row[cols[2]]) if len(cols) > 2 else ""
                    })
        except Exception as e:
            st.error(f"Erreur lors de la lecture de la feuille {sheet}: {e}")
    return pd.DataFrame(extracted_data)

# 4. Interface Utilisateur (UI)
st.markdown("<h1 class='main-header'>🏢 Système Cloud de Gestion des Fournisseurs</h1>", unsafe_allow_html=True)

db_current = load_data()

tab1, tab2, tab3 = st.tabs(["📋 Liste des Fournisseurs", "📥 Importer Excel", "➕ Ajouter Manuellement"])

with tab1:
    st.subheader("Base de données des fournisseurs")
    if not db_current.empty:
        # Barre de recherche
        query = st.text_input("🔍 Rechercher par nom, catégorie ou contact :")
        
        display_df = db_current.copy()
        if query:
            mask = display_df.astype(str).apply(lambda x: x.str.contains(query, case=False, na=False)).any(axis=1)
            display_df = display_df[mask]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # Bouton d'exportation
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Fournisseurs')
        
        st.download_button(
            label="📥 Télécharger la liste (Excel)",
            data=buffer.getvalue(),
            file_name=f"Backup_Fournisseurs_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.ms-excel"
        )
    else:
        st.info("La base de données est vide. Veuillez importer un fichier ou ajouter un fournisseur.")

with tab2:
    st.subheader("Importer des données depuis Excel")
    up_file = st.file_uploader("Choisir un fichier .xlsx", type="xlsx")
    
    if up_file:
        xl = pd.ExcelFile(up_file)
        sheets = st.multiselect("Sélectionner les feuilles (Catégories) :", xl.sheet_names, default=xl.sheet_names)
        
        if st.button("🚀 Fusionner et Sauvegarder"):
            with st.spinner("Traitement en cours..."):
                new_data = process_excel_robust(up_file, sheets)
                if not new_data.empty:
                    # Fusion et suppression des doublons basées sur le Nom
                    updated_db = pd.concat([st.session_state.db, new_data]).drop_duplicates(subset=['Nom'], keep='first')
