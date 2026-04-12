import streamlit as st
import pandas as pd
import io

# 1. Configuration de la page
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# Style CSS pour une interface épurée
st.markdown("""
    <style>
    .stDataFrame { border-radius: 10px; }
    .stButton>button { border-radius: 5px; height: 3em; }
    .status-box { padding: 20px; border-radius: 10px; background-color: #f0f2f6; margin-bottom: 20px; }
    </style>
    """, unsafe_allow_html=True)

# 2. Fonction de nettoyage "Ultra-Robuste"
def ultra_robust_clean(df):
    """Nettoie le DataFrame en forçant tout en texte pour éviter l'erreur 'float found'"""
    if df.empty:
        return df

    # ÉTAPE CRUCIALE : Convertir absolument tout le contenu en chaînes de caractères dès le début
    # Cela élimine les erreurs liées aux nombres (floats) lors du nettoyage des espaces
    df = df.fillna('').astype(str)

    # Dictionnaire de mappage intelligent des colonnes (Français / Arabe / Anglais)
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'tél/mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # Recherche de la ligne d'en-tête (parfois l'en-tête n'est pas à la ligne 0)
    best_header_row = 0
    max_matches = 0
    
    # On scanne les 10 premières lignes pour trouver celle qui ressemble à un en-tête
    for i in range(min(10, len(df))):
        row_content = " ".join(df.iloc[i].values).lower()
        matches = sum(1 for keys in mapping.values() if any(k in row_content for k in keys))
        if matches > max_matches:
            max_matches = matches
            best_header_row = i

    if max_matches > 0:
        df.columns = df.iloc[best_header_row]
        df = df.iloc[best_header_row + 1:].reset_index(drop=True)

    # Renommage des colonnes
    new_cols = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keys in mapping.items():
            if any(k in c_low for k in keys):
                new_cols[col] = target
                break
    
    df = df.rename(columns=new_cols)

    # Garder uniquement les colonnes identifiées
    final_cols = [v for v in mapping.keys() if v in df.columns]
    if final_cols:
        df = df[final_cols]
    
    # Nettoyage final des espaces (maintenant sécurisé car tout est 'str')
    for col in df.columns:
        df[col] = df[col].str.strip()

    # Supprimer les lignes totalement vides ou sans nom de fournisseur
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'] != ""]
    
    return df.reset_index(drop=True)

# 3. Initialisation de la base de données (Session State)
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=[
        'Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'
    ])

# --- Interface Utilisateur ---
st.title("🏢 Gestionnaire des Fournisseurs")

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Nouveau Fournisseur (Manuel)"])

# ONGLET 1 : IMPORTATION EXCEL
with tab1:
    st.subheader("Importer depuis Excel")
    uploaded_file = st.file_uploader("Choisir un fichier .xlsx", type=['xlsx'])
    
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            all_sheets = xl.sheet_names
            
            selected_sheets = st.multiselect(
                "Sélectionnez les feuilles (catégories) à importer :", 
                all_sheets, 
                default=all_sheets
            )
            
            if st.button("🚀 Traiter et Fusionner"):
                temp_frames = []
                progress_bar = st.progress(0)
                
                for idx, sheet in enumerate(selected_sheets):
                    # Lire la feuille sans type spécifique d'abord
                    raw_df = pd.read_excel(uploaded_file, sheet_name=sheet)
                    # Nettoyer avec notre fonction robuste
                    clean_df = ultra_robust_clean(raw_df)
                    
                    if not clean_df.empty:
                        clean_df['Catégorie'] = sheet
                        temp_frames.append(clean_df)
                    
                    progress_bar.progress((idx + 1) / len(selected_sheets))
                
                if temp_frames:
                    new_entries = pd.concat(temp_frames, axis=0, ignore_index=True)
                    # Fusionner avec l'existant et supprimer les doublons
                    st.session_state.master_db = pd.concat([st.session_state.master_db, new_entries], ignore_index=True).drop_duplicates()
                    st.success(f"✅ Opération réussie : {len(new_entries)} fournisseurs ajoutés/mis à jour.")
                else:
                    st.warning("⚠️ Aucune donnée valide n'a été trouvée dans les feuilles sélectionnées.")
                    
        except Exception as e:
            st.error(f"Erreur lors de la lecture : {e}")

# ONGLET 2 : SAISIE MANUELLE
with tab2:
    st.subheader("Ajout manuel d'un fournisseur")
    with st.form("manual_entry_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            m_name = st.text_input("Nom / Raison Sociale *")
            m_cat = st.text_input("Catégorie (ex: Bureautique)")
            m_tel = st.text_input("Téléphone Fixe")
        with col2:
            m_mob = st.text_input("Mobile")
            m_mail = st.text_input("E-mail")
            m_addr = st.text_area("Adresse", height=68)
        
        submitted = st.form_submit_button("💾 Enregistrer")
        if submitted:
            if m_name:
                new_row = pd.DataFrame([{
                    "Nom du Fournisseur": m_name,
                    "Catégorie": m_cat,
                    "Téléphone": m_tel,
                    "Mobile": m_mob,
                    "Adresse": m_addr,
                    "E-mail": m_mail
                }])
                st.session_state.master_db = pd.concat([st.session_state.master_db, new_row], ignore_index=True)
                st.success(f"Le fournisseur '{m_name}' a été ajouté.")
            else:
                st.error("Le nom du fournisseur est obligatoire.")

# 4. AFFICHAGE DES RÉSULTATS
st.divider()
if not st.session_state.master_db.empty:
    st.subheader("📋 Liste Globale des Fournisseurs")
    
    # Barre de recherche
    search_query = st.text_input("🔍 Rechercher par nom, catégorie ou ville :")
    
    display_df = st.session_state.master_db
    if search_query:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search_query, case=False)).any(axis=1)
        display_df = display_df[mask]

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # Export et Actions
    c_exp1, c_exp2 = st.columns([1, 1])
    with c_exp1:
        # Export Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            display_df.to_excel(writer, index=False, sheet_name='Fournisseurs')
        
        st.download_button(
            label="📥 Télécharger la liste en Excel",
            data=output.getvalue(),
            file_name="base_fournisseurs_finale.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with c_exp2:
        if st.button("🗑️ Réinitialiser la base"):
            st.session_state.master_db = pd.DataFrame(columns=st.session_state.master_db.columns)
            st.rerun()
else:
    st.info("La base de données est vide. Utilisez l'un des onglets ci-dessus pour ajouter des données.")
