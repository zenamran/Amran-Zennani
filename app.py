import streamlit as st
import pandas as pd
import io

# 1. Configuration de la page
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# Style CSS pour une interface professionnelle
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    html, body, [class*="css"] {
        font-family: 'Segoe UI', sans-serif;
    }
    .stDataFrame { border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.05); }
    .stButton>button { border-radius: 6px; font-weight: 600; height: 3em; transition: 0.3s; }
    .stButton>button:hover { border-color: #10B981; color: #10B981; }
    .main-header { color: #1E293B; font-weight: 700; margin-bottom: 1rem; }
    </style>
    """, unsafe_allow_html=True)

# 2. Fonction de nettoyage "Ultra-Robuste" V3
def ultra_robust_clean(df):
    """Nettoie le DataFrame en gérant les types mixtes et en trouvant l'en-tête optimal"""
    if df.empty:
        return df

    # Convertir tout en texte dès le départ pour éviter les erreurs 'float'
    df = df.fillna('').astype(str)

    # Mappage des colonnes (Français, Arabe, Anglais)
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'etablissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'tél/mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # Stratégie de détection d'en-tête améliorée
    best_header_row = -1
    max_matches = 0
    
    # On scanne les 15 premières lignes pour trouver le véritable en-tête
    for i in range(min(15, len(df))):
        row_content = " ".join(df.iloc[i].values).lower()
        matches = sum(1 for keys in mapping.values() if any(k in row_content for k in keys))
        if matches > max_matches:
            max_matches = matches
            best_header_row = i

    if best_header_row != -1:
        df.columns = [str(c).strip() for c in df.iloc[best_header_row]]
        df = df.iloc[best_header_row + 1:].reset_index(drop=True)

    # Renommage intelligent
    new_cols = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keys in mapping.items():
            if any(k in c_low for k in keys):
                new_cols[col] = target
                break
    
    df = df.rename(columns=new_cols)

    # Conserver uniquement les colonnes identifiées
    final_cols = [v for v in mapping.keys() if v in df.columns]
    if final_cols:
        df = df[final_cols]
    
    # Nettoyage des espaces blancs résiduels
    df = df.apply(lambda x: x.str.strip())

    # Supprimer les lignes où le nom du fournisseur est vide ou ressemble à un en-tête répété
    if 'Nom du Fournisseur' in df.columns:
        # On évite les lignes qui contiennent le mot 'Nom' ou 'Désignation' comme valeur (doublons d'en-tête)
        df = df[df['Nom du Fournisseur'] != ""]
        df = df[~df['Nom du Fournisseur'].str.lower().isin(['nom', 'nom du fournisseur', 'désignation', 'designation'])]
    
    return df.reset_index(drop=True)

# 3. Initialisation de l'état (Base de données locale)
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=[
        'Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'
    ])

# --- Interface ---
st.markdown("<h1 class='main-header'>🏢 Gestion des Fournisseurs Professionnels</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Saisie Manuelle"])

# ONGLET 1 : IMPORTATION
with tab1:
    st.subheader("Importer des données depuis Excel")
    uploaded_file = st.file_uploader("Glissez votre fichier .xlsx ici", type=['xlsx'])
    
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            all_sheets = xl.sheet_names
            
            st.info(f"📂 {len(all_sheets)} feuilles détectées.")
            selected_sheets = st.multiselect("Sélectionnez les catégories à importer :", all_sheets, default=all_sheets)
            
            if st.button("🔄 Lancer la fusion et le nettoyage"):
                temp_frames = []
                progress = st.progress(0)
                
                for idx, sheet in enumerate(selected_sheets):
                    # Lecture de la feuille
                    raw_df = pd.read_excel(uploaded_file, sheet_name=sheet)
                    # Nettoyage avec détection d'en-tête
                    clean_df = ultra_robust_clean(raw_df)
                    
                    if not clean_df.empty:
                        clean_df['Catégorie'] = sheet
                        temp_frames.append(clean_df)
                    
                    progress.progress((idx + 1) / len(selected_sheets))
                
                if temp_frames:
                    new_data = pd.concat(temp_frames, axis=0, ignore_index=True)
                    # Fusion et suppression des doublons stricts
                    st.session_state.master_db = pd.concat([st.session_state.master_db, new_data], ignore_index=True).drop_duplicates(subset=['Nom du Fournisseur'], keep='first')
                    st.success(f"✅ Succès : {len(new_data)} nouveaux fournisseurs importés.")
                else:
                    st.warning("⚠️ Aucun donnée exploitable trouvée dans ces feuilles.")
                    
        except Exception as e:
            st.error(f"Erreur technique : {e}")

# ONGLET 2 : SAISIE MANUELLE
with tab2:
    st.subheader("Ajouter un fournisseur manuellement")
    with st.form("form_manual", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            f_name = st.text_input("Nom / Raison Sociale *")
            f_cat = st.text_input("Catégorie / Spécialité")
            f_tel = st.text_input("Téléphone Fixe")
        with col2:
            f_mob = st.text_input("Mobile / Portable")
            f_mail = st.text_input("Adresse E-mail")
            f_addr = st.text_area("Adresse complète", height=68)
        
        if st.form_submit_button("💾 Enregistrer dans la base"):
            if f_name:
                new_entry = pd.DataFrame([{
                    "Nom du Fournisseur": f_name,
                    "Catégorie": f_cat,
                    "Téléphone": f_tel,
                    "Mobile": f_mob,
                    "Adresse": f_addr,
                    "E-mail": f_mail
                }])
                st.session_state.master_db = pd.concat([st.session_state.master_db, new_entry], ignore_index=True)
                st.success(f"✔️ Fournisseur '{f_name}' ajouté avec succès.")
            else:
                st.error("Le nom du fournisseur est obligatoire.")

# 4. RECHERCHE ET EXPORT
st.divider()
if not st.session_state.master_db.empty:
    st.subheader("📋 Liste unifiée des Fournisseurs")
    
    search = st.text_input("🔍 Rechercher (nom, téléphone, ville, catégorie...):", placeholder="Tapez votre recherche ici...")
    
    # Filtrage de la vue
    view_df = st.session_state.master_db
    if search:
        mask = view_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        view_df = view_df[mask]

    st.write(f"Affichage de **{len(view_df)}** résultats.")
    st.dataframe(view_df, use_container_width=True, hide_index=True)
    
    col_btns = st.columns([1, 1, 2])
    with col_btns[0]:
        # Export Excel
        towrite = io.BytesIO()
        with pd.ExcelWriter(towrite, engine='openpyxl') as writer:
            view_df.to_excel(writer, index=False, sheet_name='Base_Fournisseurs')
        
        st.download_button(
            label="📥 Exporter vers Excel",
            data=towrite.getvalue(),
            file_name="base_fournisseurs_nettoyee.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    with col_btns[1]:
        if st.button("🗑️ Vider la base"):
            st.session_state.master_db = pd.DataFrame(columns=st.session_state.master_db.columns)
            st.rerun()
else:
    st.info("Aucune donnée disponible. Veuillez importer un fichier ou saisir un fournisseur.")
