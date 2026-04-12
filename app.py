import streamlit as st
import pandas as pd
import io

# 1. Configuration de la page
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# Style CSS personnalisé pour un look moderne
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .stDataFrame { border-radius: 12px; }
    .stButton>button { width: 100%; border-radius: 8px; font-weight: bold; }
    .main { background-color: #fcfcfc; }
    </style>
    """, unsafe_allow_html=True)

# 2. Logique de nettoyage robuste
def robust_clean(df):
    """Nettoie le DataFrame en gérant les types mixtes et les en-têtes miltiples"""
    if df.empty:
        return df

    # Conversion forcée en chaînes de caractères pour éviter l'erreur 'float found'
    # On remplace les valeurs NaN par une chaîne vide
    df = df.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')

    # Mappage intelligent des colonnes (Reconnaissance FR/AR/EN)
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف'],
        'Mobile': ['mobile', 'mob', 'tél/mob', 'محمول', 'جوال'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد'],
        'Fax': ['fax', 'الفاكس']
    }

    # Détection de l'index de l'en-tête réel
    header_idx = 0
    found_header = False
    for i in range(min(len(df), 20)):
        row_str = " ".join(df.iloc[i].tolist()).lower()
        if any(keyword in row_str for keyword in ['désign', 'design', 'nom', 'tél', 'tel', 'fourniss']):
            header_idx = i
            found_header = True
            break
    
    if found_header:
        df.columns = [str(c).strip() for c in df.iloc[header_idx]]
        df = df.iloc[header_idx + 1:].reset_index(drop=True)

    # Renommage des colonnes selon les mots-clés
    new_cols = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keys in mapping.items():
            if any(k in c_low for k in keys):
                new_cols[col] = target
                break
    
    df = df.rename(columns=new_cols)

    # Sécurité : Si le nom n'est pas détecté
    if 'Nom du Fournisseur' not in df.columns:
        useful_cols = [c for c in df.columns if 'n°' not in str(c).lower()]
        if useful_cols:
            df = df.rename(columns={useful_cols[0]: 'Nom du Fournisseur'})

    # Garder les colonnes mappées uniquement
    existing_cols = [v for v in mapping.keys() if v in df.columns]
    if existing_cols:
        df = df[existing_cols]

    # Nettoyage final des espaces
    df = df.apply(lambda x: x.str.strip())
    
    # Supprimer les lignes vides basées sur le nom
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'] != ""]
    
    return df.reset_index(drop=True)

# 3. Interface principale
st.title("🏢 Gestion Centralisée des Fournisseurs")

# Initialisation de la base de données globale
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=[
        'Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'
    ])

# Menu de navigation par onglets
tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Saisie Manuelle"])

with tab1:
    st.subheader("Importation de fichiers")
    col_up1, col_up2 = st.columns([1, 2])
    
    with col_up1:
        uploaded_file = st.file_uploader("Fichier Excel (.xlsx)", type=['xlsx'])
    
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheets = xl.sheet_names
            st.write(f"📁 {len(sheets)} onglets trouvés.")
            
            selected_sheets = st.multiselect("Sélectionnez les onglets :", sheets, default=sheets)
            
            if st.button("🔄 Fusionner & Nettoyer"):
                temp_list = []
                for s in selected_sheets:
                    df_raw = pd.read_excel(uploaded_file, sheet_name=s)
                    df_clean = robust_clean(df_raw)
                    if not df_clean.empty:
                        df_clean['Catégorie'] = s
                        temp_list.append(df_clean)
                
                if temp_list:
                    # Fusion avec la base existante
                    new_data = pd.concat(temp_list, axis=0, ignore_index=True, sort=False)
                    st.session_state.master_db = pd.concat([st.session_state.master_db, new_data], ignore_index=True).drop_duplicates()
                    st.success(f"✅ Importation réussie ! {len(new_data)} fournisseurs ajoutés.")
        except Exception as e:
            st.error(f"Erreur lors de l'import : {e}")

with tab2:
    st.subheader("Ajouter un nouveau fournisseur")
    with st.form("form_manual"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom de la Société *")
            category = st.text_input("Catégorie (ex: Pneumatique)")
            tel = st.text_input("Téléphone Fixe")
        with c2:
            mobile = st.text_input("Mobile")
            email = st.text_input("Email")
            address = st.text_area("Adresse Complète", height=68)
        
        if st.form_submit_button("💾 Enregistrer le fournisseur"):
            if name:
                new_entry = pd.DataFrame([{
                    "Nom du Fournisseur": name,
                    "Catégorie": category,
                    "Téléphone": tel,
                    "Mobile": mobile,
                    "Adresse": address,
                    "E-mail": email
                }])
                st.session_state.master_db = pd.concat([st.session_state.master_db, new_entry], ignore_index=True)
                st.success(f"Fournisseur '{name}' enregistré.")
            else:
                st.warning("Le champ Nom est obligatoire.")

# 4. Affichage et Recherche
if not st.session_state.master_db.empty:
    st.divider()
    search = st.text_input("🔍 Recherche rapide (par nom, catégorie, téléphone...):")
    
    df_view = st.session_state.master_db
    if search:
        mask = df_view.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        df_view = df_view[mask]

    st.write(f"📋 **{len(df_view)}** Fournisseurs affichés")
    st.dataframe(df_view, use_container_width=True, hide_index=True)

    # Actions sur la base
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        # Export Excel
        out_buf = io.BytesIO()
        with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
            df_view.to_excel(writer, index=False, sheet_name='Base_Suppliers')
        
        st.download_button("📥 Télécharger la base complète (Excel)", 
                           data=out_buf.getvalue(), 
                           file_name="Base_Fournisseurs_Organisee.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    with col_act2:
        if st.button("🗑️ Vider la base de données"):
            st.session_state.master_db = pd.DataFrame(columns=st.session_state.master_db.columns)
            st.rerun()
else:
    st.info("La base de données est vide. Importez un fichier ou saisissez un fournisseur manuellement.")
