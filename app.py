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
    .stDataFrame { border-radius: 10px; }
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 2px solid #10B981; padding-bottom: 10px; }
    .error-box { padding: 10px; background-color: #FEE2E2; border-left: 5px solid #EF4444; color: #B91C1C; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# 2. Fonction de nettoyage "Blindée" V6 (Solution définitive aux erreurs des photos)
def ultra_robust_clean(df):
    """Nettoyage capable de gérer les erreurs de type (float vs str) et les index non-uniques"""
    if df.empty:
        return df

    # --- ÉTAPE 1 : Normalisation totale ---
    # On force tout en string immédiatement pour éviter "expected str instance, float found"
    df = df.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    
    # Supprimer les lignes et colonnes totalement vides
    df = df.loc[:, ~df.columns.str.contains('^Unnamed')] if any(not str(c).startswith('Unnamed') for c in df.columns) else df
    df = df[df.apply(lambda x: "".join(x).strip() != "", axis=1)]

    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'etablissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'المنطقة', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax', 'tél/mob'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # --- ÉTAPE 2 : Détection de l'en-tête ---
    best_row_idx = -1
    max_score = 0
    
    # On cherche l'en-tête sur les 30 premières lignes
    for i in range(min(30, len(df))):
        row_values = [str(val).lower() for val in df.iloc[i].values]
        score = 0
        for target, keywords in mapping.items():
            if any(any(k in val for k in keywords) for val in row_values):
                score += 1
        
        if score > max_score:
            max_score = score
            best_row_idx = i

    # Si un en-tête est trouvé, on l'applique
    if best_row_idx != -1 and max_score >= 1:
        new_header = [str(c).strip() for c in df.iloc[best_row_idx]]
        df.columns = new_header
        df = df.iloc[best_row_idx + 1:].reset_index(drop=True)
    else:
        # Sinon, on nomme les colonnes par défaut pour éviter les index non-uniques
        df.columns = [f"Col_{i}" for i in range(len(df.columns))]

    # --- ÉTAPE 3 : Mapping et Renommage ---
    rename_map = {}
    used_targets = set()
    
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keywords in mapping.items():
            if target not in used_targets and any(k in c_low for k in keywords):
                rename_map[col] = target
                used_targets.add(target)
                break
    
    df = df.rename(columns=rename_map)

    # Sécurité : Si 'Nom du Fournisseur' n'est toujours pas identifié
    if 'Nom du Fournisseur' not in df.columns:
        # On cherche la première colonne qui n'est pas un numéro (N°, ID, etc.)
        for col in df.columns:
            if not any(k in str(col).lower() for k in ['n°', 'id', 'index', 'n_']):
                df = df.rename(columns={col: 'Nom du Fournisseur'})
                break

    # --- ÉTAPE 4 : Filtrage Final ---
    standard_cols = ['Nom du Fournisseur', 'Adresse', 'Téléphone', 'Mobile', 'E-mail']
    existing_cols = [c for c in standard_cols if c in df.columns]
    
    if existing_cols:
        df = df[existing_cols]
    
    # Nettoyage des textes
    for col in df.columns:
        df[col] = df[col].str.strip()

    # Supprimer les lignes où le nom est vide ou est une répétition de l'en-tête
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'] != ""]
        header_keywords = ['nom', 'designation', 'fournisseur', 'اسم', 'المورد', 'établissement']
        df = df[~df['Nom du Fournisseur'].str.lower().isin(header_keywords)]
        # Suppression des lignes de titres/en-têtes restants
        df = df[~df['Nom du Fournisseur'].str.contains('^[0-9]+$', na=False)] # Supprime si c'est juste un index numérique

    return df.reset_index(drop=True)

# 3. Initialisation du State
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])

st.markdown("<h1 class='main-header'>🏢 Gestionnaire de Fournisseurs (Version Stable)</h1>", unsafe_allow_html=True)

t1, t2 = st.tabs(["📥 Import Excel Intelligent", "➕ Ajout Manuel"])

with t1:
    file = st.file_uploader("Charger votre fichier Excel (.xlsx)", type=['xlsx'])
    if file:
        try:
            xl = pd.ExcelFile(file)
            sheets = st.multiselect("Sélectionnez les feuilles à traiter", xl.sheet_names, default=xl.sheet_names)
            
            if st.button("🚀 Lancer l'importation"):
                all_data = []
                for s in sheets:
                    try:
                        raw = pd.read_excel(file, sheet_name=s)
                        cleaned = ultra_robust_clean(raw)
                        if not cleaned.empty:
                            cleaned['Catégorie'] = s
                            all_data.append(cleaned)
                    except Exception as sheet_err:
                        st.warning(f"Feuille '{s}' ignorée : {sheet_err}")
                
                if all_data:
                    # Fusion des nouvelles données
                    new_df = pd.concat(all_data, axis=0, ignore_index=True)
                    
                    # Fusion avec la base existante sans erreurs d'index
                    current_db = st.session_state.master_db
                    combined = pd.concat([current_db, new_df], axis=0, ignore_index=True)
                    
                    # Nettoyage final des doublons
                    if 'Nom du Fournisseur' in combined.columns:
                        st.session_state.master_db = combined.drop_duplicates(subset=['Nom du Fournisseur'], keep='first').reset_index(drop=True)
                        st.success(f"✅ Importation réussie : {len(new_df)} lignes ajoutées.")
                    else:
                        st.error("Erreur : Impossible de définir la colonne 'Nom du Fournisseur'.")
                else:
                    st.error("Aucune donnée n'a pu être extraite du fichier.")
        except Exception as e:
            st.error(f"Erreur lors de la lecture du fichier : {str(e)}")

with t2:
    with st.form("manual_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom / Raison Sociale *")
            cat = st.text_input("Catégorie")
            tel = st.text_input("Téléphone")
        with c2:
            mob = st.text_input("Mobile")
            mail = st.text_input("E-mail")
            adr = st.text_area("Adresse")
        
        if st.form_submit_button("💾 Enregistrer"):
            if name:
                new_row = pd.DataFrame([{"Nom du Fournisseur": name, "Catégorie": cat, "Téléphone": tel, "Mobile": mob, "Adresse": adr, "E-mail": mail}])
                st.session_state.master_db = pd.concat([st.session_state.master_db, new_row], ignore_index=True).drop_duplicates(subset=['Nom du Fournisseur'])
                st.success(f"Fournisseur {name} enregistré.")
            else: st.warning("Le nom est obligatoire.")

# 4. Affichage et Export
st.divider()
if not st.session_state.master_db.empty:
    db = st.session_state.master_db
    st.subheader(f"📋 Base de données ({len(db)} fournisseurs)")
    
    search = st.text_input("🔍 Rechercher un fournisseur...")
    if search:
        db = db[db.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)]
    
    st.dataframe(db, use_container_width=True, hide_index=True)
    
    col_ex1, col_ex2, _ = st.columns([1, 1, 2])
    with col_ex1:
        towrite = io.BytesIO()
        db.to_excel(towrite, index=False, engine='openpyxl')
        st.download_button("📥 Télécharger (Excel)", towrite.getvalue(), "base_fournisseurs.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    with col_ex2:
        if st.button("🗑️ Vider la base"):
            st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])
            st.rerun()
else:
    st.info("La base de données est vide. Importez un fichier pour commencer.")
