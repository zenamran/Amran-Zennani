import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import io
import json

if not firebase_admin._apps:
    cred = credentials.Certificate(json.loads(st.secrets["firebase_json"]))
    firebase_admin.initialize_app(cred)

db = firestore.client()
# 🔥 تحميل البيانات
def load_from_firebase():
    docs = db.collection("suppliers").stream()
    data = []
    for doc in docs:
        data.append(doc.to_dict())
    return data

# 🔥 حفظ البيانات
def save_to_firebase(data):
    docs = db.collection("suppliers").stream()
    for doc in docs:
        doc.reference.delete()

    for item in data:
        db.collection("suppliers").add(item)

# 1. الإعدادات العامة للصفحة
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# تصميم الواجهة
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 3px solid #10B981; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# قائمة الفئات
AVAILABLE_CATEGORIES = [
    "Mécanique", "Électricité", "Plomberie", "PPE / Protection", 
    "Consommables", "Pièces de rechange", "Outillage", 
    "Maintenance", "Informatique", "Produits Chimiques", "BTP"
]

# معالجة Excel
def get_clean_records(df_raw, category_name):
    if df_raw.empty: return []
    
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل'],
        'FAX': ['FAX', 'Fax', 'fax','الفاكس' ,'فاكس']
    }

    header_idx = -1
    col_map = {}
    for i in range(min(50, len(df))):
        row = [str(x).lower() for x in df.iloc[i].values]
        current_map = {}
        matches = 0
        for target, keys in mapping.items():
            for idx, cell in enumerate(row):
                if any(k in cell for k in keys):
                    current_map[idx] = target
                    matches += 1
                    break
        if matches >= 1:
            header_idx, col_map = i, current_map
            break

    records = []
    if header_idx != -1:
        data_rows = df.iloc[header_idx + 1:]
        for _, row in data_rows.iterrows():
            record = {'Catégories': category_name}
            for target in mapping.keys(): record[target] = ""
            for col_idx, target_name in col_map.items():
                record[target_name] = str(row.iloc[col_idx]).strip()
            
            if record.get('Nom du Fournisseur') and record['Nom du Fournisseur'].lower() not in ['nom', 'designation', 'fournisseur', 'اسم']:
                records.append(record)
    return records

# 🔥 تحميل أولي من Firebase
if 'data_list' not in st.session_state:
    st.session_state.data_list = load_from_firebase()

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Ajout Manuel"])

# 📥 Import Excel
with tab1:
    uploaded_file = st.file_uploader("Charger un fichier Excel", type=['xlsx'])
    if uploaded_file:
        xl = pd.ExcelFile(uploaded_file)
        sheets = st.multiselect("Feuilles :", xl.sheet_names, default=xl.sheet_names)
        
        if st.button("🚀 Fusionner"):
            for s in sheets:
                df_raw = pd.read_excel(uploaded_file, sheet_name=s, header=None)
                records = get_clean_records(df_raw, s)
                
                for rec in records:
                    name_lower = rec['Nom du Fournisseur'].lower().strip()
                    existing = next((i for i, item in enumerate(st.session_state.data_list)
                                     if item['Nom du Fournisseur'].lower().strip() == name_lower), None)
                    
                    if existing is None:
                        st.session_state.data_list.append(rec)
                    else:
                        current = str(st.session_state.data_list[existing]['Catégories'])
                        if s not in current:
                            st.session_state.data_list[existing]['Catégories'] = f"{current} / {s}"

            save_to_firebase(st.session_state.data_list)
            st.success("✅ Données enregistrées dans Firebase")

# ➕ Ajout manuel
with tab2:
    with st.form("form"):
        name = st.text_input("Nom *")
        cats = st.multiselect("Catégories", AVAILABLE_CATEGORIES)
        tel = st.text_input("Téléphone")
        if st.form_submit_button("Enregistrer"):
            if name:
                st.session_state.data_list.append({
                    "Nom du Fournisseur": name,
                    "Catégories": " / ".join(cats),
                    "Téléphone": tel
                })
                save_to_firebase(st.session_state.data_list)
                st.success("✅ Ajouté et sauvegardé")

# 📊 Affichage
if st.session_state.data_list:
    df = pd.DataFrame(st.session_state.data_list)
    st.dataframe(df, use_container_width=True)
