import streamlit as st
import pandas as pd
import io

# Configuration de la page
st.set_page_config(page_title="Gestion des Fournisseurs v2.0", layout="wide")

# Style CSS pour une interface moderne
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    .main { background-color: #f8f9fa; }
    .stDataFrame { background-color: white; border-radius: 10px; padding: 10px; }
    </style>
    """, unsafe_allow_html=True)

def ultra_robust_clean(df):
    """Fonction de nettoyage avancée pour éviter les erreurs de type de données"""
    if df.empty:
        return df

    # Conversion forcée de tout le DataFrame en chaînes de caractères pour éviter l'erreur 'float found'
    df = df.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')

    # Dictionnaire de mappage des colonnes
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف'],
        'Mobile': ['mobile', 'mob', 'tél/mob', 'محمول'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد'],
        'Fax': ['fax', 'الفاكس']
    }

    # 1. Recherche automatique de l'en-tête
    header_idx = 0
    found_header = False
    for i in range(min(len(df), 20)):
        row_content = " ".join(df.iloc[i].values).lower()
        if any(keyword in row_content for keyword in ['désign', 'design', 'nom', 'tél', 'tel']):
            header_idx = i
            found_header = True
            break
    
    if found_header:
        df.columns = [str(c).strip() for c in df.iloc[header_idx]]
        df = df.iloc[header_idx + 1:].reset_index(drop=True)

    # 2. Nettoyage des noms de colonnes et mappage
    new_cols = {}
    for col in df.columns:
        c_low = str(col).lower().strip()
        for target, keys in mapping.items():
            if any(k in c_low for k in keys):
                new_cols[col] = target
                break
    
    df = df.rename(columns=new_cols)

    # 3. Sécurité : Si 'Nom du Fournisseur' n'est pas détecté, prendre la 1ère colonne utile
    if 'Nom du Fournisseur' not in df.columns:
        cols = [c for c in df.columns if 'n°' not in str(c).lower()]
        if cols:
            df = df.rename(columns={cols[0]: 'Nom du Fournisseur'})

    # 4. Garder uniquement les colonnes identifiées
    important_cols = [v for v in mapping.keys() if v in df.columns]
    if important_cols:
        df = df[important_cols]

    # 5. Nettoyage final des espaces et suppression des lignes vides
    df = df.apply(lambda x: x.str.strip() if x.dtype == "object" else x)
    if 'Nom du Fournisseur' in df.columns:
        df = df[df['Nom du Fournisseur'] != ""]
    
    return df.reset_index(drop=True)

st.title("🛡️ Gestionnaire de Fournisseurs Multi-Feuilles")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame()

# Sidebar pour le chargement
with st.sidebar:
    st.header("📁 Importation")
    file = st.file_uploader("Fichier Excel (.xlsx)", type=['xlsx'])

if file:
    try:
        excel_obj = pd.ExcelFile(file)
        sheets = excel_obj.sheet_names
        
        st.info(f"✅ {len(sheets)} onglets détectés dans le fichier.")
        selected_sheets = st.multiselect("Sélectionnez les feuilles à fusionner :", sheets, default=sheets)
        
        if st.button("🚀 Fusionner les données"):
            all_data = []
            progress = st.progress(0)
            
            for i, s_name in enumerate(selected_sheets):
                df_raw = pd.read_excel(file, sheet_name=s_name)
                # Utilisation de la fonction ultra-robuste
                df_clean = ultra_robust_clean(df_raw)
                if not df_clean.empty:
                    df_clean['Source'] = s_name
                    all_data.append(df_clean)
                progress.progress((i + 1) / len(selected_sheets))
            
            if all_data:
                st.session_state.db = pd.concat(all_data, axis=0, ignore_index=True, sort=False)
                st.success(f"Traitement terminé : {len(st.session_state.db)} fournisseurs trouvés.")
            else:
                st.error("Aucune donnée valide n'a pu être extraite.")
                
    except Exception as e:
        st.error(f"Erreur de lecture : {e}")

# Zone d'affichage et de recherche
if not st.session_state.db.empty:
    st.divider()
    search = st.text_input("🔍 Rechercher un nom, un téléphone ou une ville :")
    
    res_df = st.session_state.db
    if search:
        mask = res_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        res_df = res_df[mask]
    
    st.write(f"Affichage de **{len(res_df)}** lignes.")
    st.dataframe(res_df, use_container_width=True, hide_index=True)
    
    # Exportation
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        res_df.to_excel(writer, index=False, sheet_name='Resultats')
    
    st.download_button("📥 Télécharger la base unifiée (Excel)", 
                       data=buf.getvalue(), 
                       file_name="Base_Fournisseurs_Pro.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.markdown("""
    ### Bienvenue
    1. Chargez votre fichier Excel dans la barre latérale.
    2. Choisissez les onglets à inclure.
    3. Cliquez sur **Fusionner** pour nettoyer automatiquement tous vos fournisseurs.
    """)
