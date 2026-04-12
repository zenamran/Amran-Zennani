import streamlit as st
import pandas as pd
import io

# Configuration de la page
st.set_page_config(page_title="Système de Gestion des Fournisseurs", layout="wide")

# Style CSS pour améliorer l'affichage
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .stDataFrame { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

def robust_clean(df):
    """Fonction intelligente pour nettoyer et structurer les données Excel"""
    if df.empty:
        return df

    # Dictionnaire de mappage (Français/Arabe/Anglais)
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'اسم المورد', 'شركة'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'العنوان'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'الهاتف'],
        'Mobile': ['mobile', 'mob', 'tél/mob', 'محمول', 'جوال'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد'],
        'Fax': ['fax', 'الفاكس']
    }

    # 1. Détecter l'index de l'en-tête (Header)
    actual_header_index = 0
    found = False
    for i in range(min(len(df), 20)):
        row_str = " ".join(df.iloc[i].astype(str).tolist()).lower()
        if any(keyword in row_str for keyword in ['désign', 'design', 'nom', 'tél', 'tel', 'اسم']):
            actual_header_index = i
            found = True
            break
    
    if found:
        df.columns = [str(c).strip() for c in df.iloc[actual_header_index]]
        df = df.iloc[actual_header_index + 1:].reset_index(drop=True)

    # 2. Renommer les colonnes selon le dictionnaire
    new_cols = {}
    for col in df.columns:
        col_lower = str(col).lower()
        for standard_name, keywords in mapping.items():
            if any(key in col_lower for key in keywords):
                new_cols[col] = standard_name
                break
    
    df = df.rename(columns=new_cols)

    # 3. Fallback: Si le nom n'est pas trouvé, prendre la première colonne non numérique
    if 'Nom du Fournisseur' not in df.columns:
        potential = [c for c in df.columns if 'n°' not in str(c).lower() and 'num' not in str(c).lower()]
        if potential:
            df = df.rename(columns={potential[0]: 'Nom du Fournisseur'})

    # 4. Nettoyage des cellules (Correction des types float/str)
    def clean_cell(x):
        if pd.isna(x) or str(x).lower() in ['nan', 'none', 'null']: return ""
        return str(x).strip()

    df = df.map(clean_cell)
    
    # 5. Filtrer les colonnes importantes
    valid_cols = [v for v in mapping.keys() if v in df.columns]
    if valid_cols:
        df = df[valid_cols]

    # 6. Supprimer les lignes vides ou sans nom
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'] != ""]
    
    return df.reset_index(drop=True)

st.title("🛡️ Portail de Gestion des Fournisseurs")

if 'final_db' not in st.session_state:
    st.session_state.final_db = pd.DataFrame()

# Tabs pour l'interface
tab_upload, tab_manual = st.tabs(["📥 Import & Fusion", "➕ Ajout Manuel"])

with tab_upload:
    with st.sidebar:
        st.header("⚙️ Configuration")
        uploaded_file = st.file_uploader("Charger un fichier Excel (.xlsx)", type=['xlsx'])
        
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            all_sheets = xl.sheet_names
            
            st.info(f"📂 {len(all_sheets)} catégories (onglets) détectées.")
            selected = st.multiselect("Sélectionnez les catégories à fusionner :", all_sheets, default=all_sheets)
            
            if st.button("🚀 Traiter et Fusionner"):
                combined_list = []
                progress_bar = st.progress(0)
                
                for index, sheet in enumerate(selected):
                    df_raw = pd.read_excel(uploaded_file, sheet_name=sheet)
                    cleaned = robust_clean(df_raw)
                    if not cleaned.empty:
                        cleaned['Catégorie'] = sheet
                        combined_list.append(cleaned)
                    progress_bar.progress((index + 1) / len(selected))
                
                if combined_list:
                    st.session_state.final_db = pd.concat(combined_list, axis=0, ignore_index=True, sort=False)
                    st.success(f"✅ Fusion réussie : {len(st.session_state.final_db)} fournisseurs importés.")
                else:
                    st.warning("Aucune donnée valide trouvée dans les onglets sélectionnés.")

        except Exception as e:
            st.error(f"Erreur lors de la lecture : {str(e)}")

with tab_manual:
    st.header("Nouveau Fournisseur")
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            m_name = st.text_input("Nom du Fournisseur / Société *")
            m_tel = st.text_input("Téléphone Fixe")
            m_mob = st.text_input("Mobile")
        with col2:
            m_cat = st.text_input("Catégorie / Secteur")
            m_addr = st.text_input("Adresse")
            m_mail = st.text_input("Email")
        
        if st.form_submit_button("Enregistrer"):
            if m_name:
                new_row = pd.DataFrame([{
                    "Nom du Fournisseur": m_name,
                    "Téléphone": m_tel,
                    "Mobile": m_mob,
                    "Adresse": m_addr,
                    "E-mail": m_mail,
                    "Catégorie": m_cat
                }])
                st.session_state.final_db = pd.concat([st.session_state.final_db, new_row], ignore_index=True)
                st.success(f"✅ Fournisseur '{m_name}' ajouté avec succès.")
            else:
                st.error("Veuillez saisir au moins le nom du fournisseur.")

# Affichage des résultats
if not st.session_state.final_db.empty:
    st.markdown("---")
    
    search_q = st.text_input("🔍 Rechercher un fournisseur, téléphone ou catégorie :", placeholder="Tapez ici...")
    
    df_display = st.session_state.final_db
    if search_q:
        mask = df_display.astype(str).apply(lambda x: x.str.contains(search_q, case=False, na=False)).any(axis=1)
        df_display = df_display[mask]

    st.write(f"📊 **{len(df_display)}** Fournisseurs trouvés.")
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    # Export Excel
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_display.to_excel(writer, index=False, sheet_name='Base_Donnees')
    
    st.download_button(
        label="📥 Télécharger la base de données (Excel)",
        data=buffer.getvalue(),
        file_name="Base_Fournisseurs_Unifiee.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    if not uploaded_file:
        st.info("Veuillez charger un fichier Excel ou utiliser l'ajout manuel pour commencer.")
