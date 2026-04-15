import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import pandas as pd
import io
import json
# --- 1. تهيئة Firebase في أعلى الملف ---
# نضع db في البداية لضمان وصول الدوال إليه
if not firebase_admin._apps:
    try:
        secrets_raw = st.secrets["firebase_json"]
        if isinstance(secrets_raw, str):
            cred_info = json.loads(secrets_raw, strict=False)
        else:
            cred_info = dict(secrets_raw)
            
        cred = credentials.Certificate(cred_info)
        firebase_admin.initialize_app(cred)
    except Exception as e:
        st.error(f"Erreur Initialisation Firebase: {e}")
        st.stop()

# تعريف db كمتغير عام
db = firestore.client()

# --- 2. تعريف الدوال التي تستخدم db ---

def load_from_firebase():
    """تحميل البيانات"""
    try:
        docs = db.collection("suppliers").stream()
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        st.error(f"Erreur de chargement: {e}")
        return []

def save_to_firebase_single(item):
    """حفظ أو تحديث مورد واحد"""
    try:
        # تأكد من وجود اسم للمورد لتجنب خطأ الـ ID
        if item.get('Nom du Fournisseur'):
            doc_id = str(item['Nom du Fournisseur']).lower().strip().replace("/", "_")
            db.collection("suppliers").document(doc_id).set(item)
    except Exception as e:
        st.error(f"Erreur sauvegarde Firestore: {e}")

# --- 3. باقي إعدادات واجهة Streamlit ---

st.set_page_config(page_title="Système de Gestion", layout="wide")

if 'data_list' not in st.session_state:
    st.session_state.data_list = load_from_firebase()

# ... (باقي كود الواجهة والتبويبات Tabs) ...

# 2. الإعدادات العامة
st.set_page_config(page_title="Système de Gestion des Fournisseurs", page_icon="🏢", layout="wide")

# --- واجهة المستخدم ---
st.markdown("""
    <style>
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 3px solid #10B981; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

AVAILABLE_CATEGORIES = [
    "Mécanique", "Électricité", "Plomberie", "PPE / Protection", 
    "Consommables", "Pièces de rechange", "Outillage", 
    "Maintenance", "Informatique", "Produits Chemicals", "BTP"
]

# --- منطق معالجة البيانات ---
def get_clean_records(df_raw, category_name):
    if df_raw.empty: return []
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد'],
        'Adresse': ['adresse', 'address', 'lieu', 'عنوان'],
        'Téléphone': ['tél', 'tel', 'phone', 'هاتف'],
        'Mobile': ['mobile', 'mob', 'محمول'],
        'E-mail': ['email', 'e-mail', 'mail', 'بريد'],
        'FAX': ['fax', 'فاكس']
    }
    header_idx = -1
    col_map = {}
    for i in range(min(20, len(df))):
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
            for col_idx, target_name in col_map.items():
                record[target_name] = str(row.iloc[col_idx]).strip()
            if record.get('Nom du Fournisseur') and record['Nom du Fournisseur'].lower() not in ['nom', 'fournisseur']:
                records.append(record)
    return records

# --- إدارة الحالة (Session State) ---
if 'data_list' not in st.session_state:
    st.session_state.data_list = load_from_firebase()

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Ajout Manuel"])

with tab1:
    uploaded_file = st.file_uploader("Charger un fichier Excel", type=['xlsx'])
    if uploaded_file:
        xl = pd.ExcelFile(uploaded_file)
        sheets = st.multiselect("Sélectionnez les feuilles :", xl.sheet_names, default=xl.sheet_names)
        
        if st.button("🚀 Fusionner"):
            progress_bar = st.progress(0)
            for idx, s in enumerate(sheets):
                df_raw = pd.read_excel(uploaded_file, sheet_name=s, header=None)
                records = get_clean_records(df_raw, s)
                
                for rec in records:
                    name_lower = rec['Nom du Fournisseur'].lower().strip()
                    existing_idx = next((i for i, item in enumerate(st.session_state.data_list) 
                                       if item['Nom du Fournisseur'].lower().strip() == name_lower), None)
                    
                    if existing_idx is None:
                        st.session_state.data_list.append(rec)
                        save_to_firebase_single(rec)
                    else:
                        # دمج الفئات إذا كان المورد موجوداً مسبقاً
                        current_cats = str(st.session_state.data_list[existing_idx].get('Catégories', ''))
                        if s not in current_cats:
                            st.session_state.data_list[existing_idx]['Catégories'] = f"{current_cats} / {s}"
                        save_to_firebase_single(st.session_state.data_list[existing_idx])
                
                progress_bar.progress((idx + 1) / len(sheets))
            st.success("✅ تم التحديث والمزامنة مع Firebase")
            st.rerun()

with tab2:
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nom de l'établissement")
            cats = st.multiselect("Catégories", AVAILABLE_CATEGORIES)
            Adresse = st.text_input("Adresse") 
            
        with col2:
            tel = st.text_input("Téléphone FIX")
            Mobile = st.text_input("Téléphone Mobile")
            email = st.text_input("E-mail")
            FAX = st.text_input("FAX")
        
        if st.form_submit_button("💾 Enregistrer"):
            if name:
                new_item = {
                    "Nom du Fournisseur": name,
                    "Catégories": " / ".join(cats),
                    "Téléphone": tel,
                    "E-mail": email,
                    "Adresse": Adresse,
                    "Mobile": Mobile,
                    "FAX": FAX
                }
                save_to_firebase_single(new_item)
                st.session_state.data_list = load_from_firebase() # تحديث القائمة
                st.success("✅ تم الحفظ بنجاح")
                st.rerun()
            else:
                st.error("يرجى إدخال اسم المورد")

# --- عرض النتائج مع ميزة البحث ---
st.divider()
if st.session_state.data_list:
    df = pd.DataFrame(st.session_state.data_list)
    
    search = st.text_input("🔍 Rechercher (Nom OU Catégorie) :")
    if search:
        df = df[df.apply(lambda row: row.astype(str).str.contains(search, case=False).any(), axis=1)]
    
    st.subheader(f"📋 Liste des fournisseurs ({len(df)})")
    st.dataframe(df, use_container_width=True, hide_index=True)
    
    # زر الحذف (Firebase)
    if st.button("🗑️ Vider l'affichage"):
        st.session_state.data_list = []
        st.rerun()
