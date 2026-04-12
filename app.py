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
    </style>
    """, unsafe_allow_html=True)

# 2. Fonction de nettoyage "Infaillible" V5
def ultra_robust_clean(df):
    """Nettoyage extrême pour gérer tous les formats d'Excel"""
    if df.empty:
        return df

    # Conversion en texte et suppression des lignes totalement vides
    df = df.fillna('').astype(str)
    df = df[df.apply(lambda x: "".join(x).strip() != "", axis=1)]

    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'etablissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'المنطقة'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'tél/mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # Trouver le meilleur en-tête
    best_row_idx = 0
    max_score = 0
    for i in range(min(25, len(df))):
        row_str = " ".join(df.iloc[i].values).lower()
        score = sum(1 for keys in mapping.values() if any(k in row_str for k in keys))
        if score > max_score:
            max_score = score
            best_row_idx = i

    # Si on a trouvé un en-tête plausible
    if max_score > 0:
        df.columns = [str(c).strip() for c in df.iloc[best_row_idx]]
        df = df.iloc[best_row_idx + 1:].reset_index(drop=True)
    else:
        # Secours : Utiliser la première ligne comme colonnes si rien n'est trouvé
        df.columns = [f"Colonne_{i}" for i in range(len(df.columns))]

    # Renommage
    new_rename = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keys in mapping.items():
            if any(k in c_low for k in keys):
                new_rename[col] = target
                break
    
    df = df.rename(columns=new_rename)

    # Si 'Nom du Fournisseur' manque, on prend la première colonne textuelle
    if 'Nom du Fournisseur' not in df.columns and len(df.columns) > 0:
        df = df.rename(columns={df.columns[0]: 'Nom du Fournisseur'})

    # Garder uniquement les colonnes du mapping
    keep_cols = [c for c in mapping.keys() if c in df.columns]
    if keep_cols:
        df = df[keep_cols]

    # Nettoyage final : supprimer les lignes qui répètent l'en-tête
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'].str.strip() != ""]
        df = df[~df['Nom du Fournisseur'].str.lower().contains('nom|designation|fournisseur|اسم|المورد', na=False)]
    
    return df.reset_index(drop=True)

# 3. Initialisation
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])

st.markdown("<h1 class='main-header'>🏢 Gestionnaire de Fournisseurs Pro</h1>", unsafe_allow_html=True)

t1, t2 = st.tabs(["📥 Import Excel", "➕ Ajout Manuel"])

with t1:
    file = st.file_uploader("Charger un fichier Excel", type=['xlsx'])
    if file:
        xl = pd.ExcelFile(file)
        sheets = st.multiselect("Choisir les feuilles", xl.sheet_names, default=xl.sheet_names)
        
        if st.button("🚀 Fusionner les données"):
            all_new = []
            for s in sheets:
                raw = pd.read_excel(file, sheet_name=s)
                cleaned = ultra_robust_clean(raw)
                if not cleaned.empty:
                    cleaned['Catégorie'] = s
                    all_new.append(cleaned)
            
            if all_new:
                combined_new = pd.concat(all_new, ignore_index=True)
                # Fusion avec la base existante
                final_df = pd.concat([st.session_state.master_db, combined_new], ignore_index=True)
                # Supprimer les doublons sur le nom
                if 'Nom du Fournisseur' in final_df.columns:
                    st.session_state.master_db = final_df.drop_duplicates(subset=['Nom du Fournisseur'], keep='first')
                st.success(f"✅ Opération terminée. {len(combined_new)} lignes traitées.")
            else:
                st.error("Désolé, aucune donnée n'a pu être extraite. Vérifiez le format de votre fichier.")

with t2:
    with st.form("manual_entry"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nom du Fournisseur *")
            cat = st.text_input("Catégorie")
            tel = st.text_input("Téléphone")
        with col2:
            mob = st.text_input("Mobile")
            mail = st.text_input("E-mail")
            adr = st.text_area("Adresse")
        
        if st.form_submit_button("Enregistrer"):
            if name:
                entry = pd.DataFrame([{"Nom du Fournisseur": name, "Catégorie": cat, "Téléphone": tel, "Mobile": mob, "Adresse": adr, "E-mail": mail}])
                st.session_state.master_db = pd.concat([st.session_state.master_db, entry], ignore_index=True)
                st.success("Ajouté !")
            else: st.warning("Le nom est requis.")

# Affichage
st.divider()
if not st.session_state.master_db.empty:
    db = st.session_state.master_db
    search = st.text_input("🔍 Rechercher...")
    if search:
        db = db[db.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    
    st.dataframe(db, use_container_width=True, hide_index=True)
    
    # Export
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine='openpyxl') as w:
        db.to_excel(w, index=False)
    st.download_button("📥 Télécharger la base complète", out.getvalue(), "base_fournisseurs.xlsx")
    
    if st.button("🗑️ Réinitialiser la base"):
        st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])
        st.rerun()
