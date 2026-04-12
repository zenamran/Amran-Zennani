import streamlit as st
import pandas as pd
import io

# 1. Configuration de la page
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# Style CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 3px solid #10B981; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #F8FAFC; border-radius: 5px 5px 0 0; }
    </style>
    """, unsafe_allow_html=True)

# 2. Fonction de nettoyage "Anti-Erreur" V7 (Résolution des index dupliqués)
def safe_clean_dataframe(df):
    """Nettoyage radical pour éviter les erreurs d'index et de types"""
    if df.empty:
        return df

    # Étape 1 : Forcer l'unicité des colonnes dès la lecture
    # Si des colonnes ont le même nom, pandas les renomme en .1, .2 etc.
    df.columns = [f"{c}_{i}" if list(df.columns).count(c) > 1 else c for i, c in enumerate(df.columns)]
    
    # Étape 2 : Conversion totale en texte (Évite l'erreur float/str)
    df = df.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')

    # Étape 3 : Détection intelligente des colonnes
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # Trouver la ligne d'en-tête (scan profond)
    best_row = 0
    max_matches = 0
    for i in range(min(40, len(df))):
        row_str = " ".join(df.iloc[i].values).lower()
        matches = sum(1 for keys in mapping.values() if any(k in row_str for k in keys))
        if matches > max_matches:
            max_matches = matches
            best_row = i

    # Appliquer l'en-tête trouvé
    if max_matches > 0:
        new_cols = [str(c).strip() for c in df.iloc[best_row]]
        # Forcer l'unicité à nouveau
        df.columns = [f"Col_{idx}" if not c or c == 'nan' else c for idx, c in enumerate(new_cols)]
        df = df.iloc[best_row + 1:].reset_index(drop=True)

    # Renommage vers les noms standards
    final_rename = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keys in mapping.items():
            if target not in final_rename.values() and any(k in c_low for k in keys):
                final_rename[col] = target
                break
    
    df = df.rename(columns=final_rename)

    # Sécurité : Si le nom manque, prendre la première colonne exploitable
    if 'Nom du Fournisseur' not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: 'Nom du Fournisseur'})

    # Garder uniquement ce qui nous intéresse
    target_cols = ['Nom du Fournisseur', 'Adresse', 'Téléphone', 'Mobile', 'E-mail']
    df = df[[c for c in target_cols if c in df.columns]]
    
    # Nettoyage des lignes inutiles
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'].str.strip() != ""]
        # Supprimer les lignes qui sont des répétitions de l'en-tête
        header_vals = ['nom', 'designation', 'fournisseur', 'اسم', 'المورد']
        df = df[~df['Nom du Fournisseur'].str.lower().isin(header_vals)]

    return df.reset_index(drop=True)

# 3. Initialisation de la base
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Saisie Manuelle"])

with tab1:
    st.subheader("Charger un fichier Excel")
    uploaded_file = st.file_uploader("Fichier .xlsx uniquement", type=['xlsx'])
    
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            selected_sheets = st.multiselect("Feuilles à importer :", xl.sheet_names, default=xl.sheet_names)
            
            if st.button("🚀 Fusionner les données"):
                temp_list = []
                for sheet in selected_sheets:
                    data = pd.read_excel(uploaded_file, sheet_name=sheet)
                    clean_data = safe_clean_dataframe(data)
                    if not clean_data.empty:
                        clean_data['Catégorie'] = sheet
                        temp_list.append(clean_data)
                
                if temp_list:
                    # On s'assure que chaque dataframe a des colonnes uniques avant concat
                    new_batch = pd.concat(temp_list, axis=0, ignore_index=True).reset_index(drop=True)
                    
                    # Fusion avec la base globale
                    combined = pd.concat([st.session_state.master_db, new_batch], axis=0, ignore_index=True)
                    
                    # Suppression définitive des doublons sur le nom
                    if 'Nom du Fournisseur' in combined.columns:
                        st.session_state.master_db = combined.drop_duplicates(subset=['Nom du Fournisseur'], keep='first').reset_index(drop=True)
                        st.success(f"✅ Importation réussie ! {len(new_batch)} fournisseurs ajoutés.")
                else:
                    st.warning("⚠️ Aucune donnée n'a été extraite.")
        except Exception as e:
            st.error(f"❌ Erreur lors de l'import : {str(e)}")

with tab2:
    st.subheader("Ajouter un fournisseur manuellement")
    with st.form("manual_form", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom de l'établissement *")
            cat = st.text_input("Catégorie")
            tel = st.text_input("Téléphone")
        with c2:
            mob = st.text_input("Mobile")
            mail = st.text_input("E-mail")
            adr = st.text_area("Adresse")
        
        if st.form_submit_button("💾 Enregistrer"):
            if name:
                new_row = pd.DataFrame([{"Nom du Fournisseur": name, "Catégorie": cat, "Téléphone": tel, "Mobile": mob, "Adresse": adr, "E-mail": mail}])
                st.session_state.master_db = pd.concat([st.session_state.master_db, new_row], ignore_index=True).drop_duplicates(subset=['Nom du Fournisseur']).reset_index(drop=True)
                st.success(f"Fournisseur '{name}' ajouté.")
            else:
                st.error("Le nom est obligatoire.")

# 4. Affichage et Gestion de la base
st.divider()
if not st.session_state.master_db.empty:
    db = st.session_state.master_db
    st.subheader(f"📊 Base de données unifiée ({len(db)} fournisseurs)")
    
    search = st.text_input("🔍 Rechercher (nom, ville, téléphone...) :")
    if search:
        db = db[db.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)]

    st.dataframe(db, use_container_width=True, hide_index=True)
    
    col_ex1, col_ex2 = st.columns([1, 4])
    with col_ex1:
        # Export Excel
        buffer = io.BytesIO()
        db.to_excel(buffer, index=False, engine='openpyxl')
        st.download_button("📥 Exporter en Excel", buffer.getvalue(), "fournisseurs_liste.xlsx")
    
    with col_ex2:
        if st.button("🗑️ Réinitialiser (Vider la base)"):
            st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])
            st.rerun()
else:
    st.info("La base est actuellement vide. Veuillez importer des données.")
