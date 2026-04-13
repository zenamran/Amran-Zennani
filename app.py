import streamlit as st
import pandas as pd
import io
import json
import os
from firebase_admin import credentials, firestore, initialize_app, _apps

# 1. إعدادات الصفحة
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# 2. تهيئة Firebase لحفظ البيانات بشكل دائم
# ملاحظة: يتم استخدام المتغيرات البيئية الموفرة في البيئة التشغيلية
def init_firestore():
    if not _apps:
        try:
            # محاولة الحصول على الإعدادات من secrets أو المتغيرات العالمية
            if "firebase" in st.secrets:
                creds_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(creds_dict)
                initialize_app(cred)
            else:
                # في بيئة التطوير المحلية، سيحاول استخدام الافتراضي
                # إذا لم يتوفر Firebase، سيعمل التطبيق في الذاكرة (Session State) فقط
                return None
        except Exception:
            return None
    return firestore.client()

db = init_firestore()
APP_ID = "fournisseurs-manager" # معرف فريد للتطبيق

# وظائف قاعدة البيانات
def save_to_cloud(data_list):
    if db:
        # المسار المعتمد: /artifacts/{appId}/public/data/{collectionName}
        for item in data_list:
            doc_id = item['Nom du Fournisseur'].replace("/", "-").strip()
            db.collection('artifacts', APP_ID, 'public', 'data', 'suppliers').document(doc_id).set(item)

def load_from_cloud():
    if db:
        try:
            docs = db.collection('artifacts', APP_ID, 'public', 'data', 'suppliers').stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            return []
    return []

# 3. تصميم الواجهة
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 3px solid #10B981; padding-bottom: 10px; }
    .stAlert { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

AVAILABLE_CATEGORIES = [
    "Mécanique", "Électricité", "Plomberie", "PPE / Protection", 
    "Consommables", "Pièces de rechange", "Outillage", 
    "Maintenance", "Informatique", "Produits Chimiques", "BTP"
]

# وظيفة معالجة الإكسيل
def get_clean_records(df_raw, category_name):
    if df_raw.empty: return []
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
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

# 4. إدارة الحالة والبيانات
if 'data_list' not in st.session_state:
    # محاولة تحميل البيانات من السحابة عند البداية
    cloud_data = load_from_cloud()
    st.session_state.data_list = cloud_data if cloud_data else []

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs (Cloud Sync)</h1>", unsafe_allow_html=True)

if not db:
    st.warning("⚠️ التطبيق يعمل حالياً في وضع الذاكرة المؤقتة. لحفظ البيانات بشكل دائم، يرجى ربط Firestore.")

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Ajout Manuel"])

with tab1:
    uploaded_file = st.file_uploader("Charger un fichier Excel", type=['xlsx'])
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheets = st.multiselect("Sélectionnez les feuilles (Catégories) :", xl.sheet_names, default=xl.sheet_names)
            
            if st.button("🚀 Fusionner et Sauvegarder"):
                new_added = 0
                for s in sheets:
                    df_raw = pd.read_excel(uploaded_file, sheet_name=s, header=None)
                    records = get_clean_records(df_raw, s)
                    
                    for rec in records:
                        name_lower = rec['Nom du Fournisseur'].lower().strip()
                        existing_idx = next((i for i, item in enumerate(st.session_state.data_list) if item['Nom du Fournisseur'].lower().strip() == name_lower), None)
                        
                        if existing_idx is None:
                            st.session_state.data_list.append(rec)
                            new_added += 1
                        else:
                            current_cats = str(st.session_state.data_list[existing_idx]['Catégories'])
                            if s.strip() not in [c.strip() for c in current_cats.split('/')]:
                                st.session_state.data_list[existing_idx]['Catégories'] = f"{current_cats} / {s}"
                
                # حفظ التغييرات في السحابة
                save_to_cloud(st.session_state.data_list)
                st.success(f"✅ تم دمج وحفظ {new_added} موردين جدد بنجاح.")
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

with tab2:
    with st.form("manual_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom de l'établissement *")
            selected_cats = st.multiselect("Sélectionner des catégories", AVAILABLE_CATEGORIES)
            custom_cat = st.text_input("Ou saisir une catégorie (كتابة فئة أخرى)")
            tel = st.text_input("Téléphone")
        with c2:
            mob = st.text_input("Mobile")
            mail = st.text_input("E-mail")
            adr = st.text_area("Adresse")
        
        if st.form_submit_button("💾 Enregistrer dans le Cloud"):
            if name:
                all_cats = list(selected_cats)
                if custom_cat.strip(): all_cats.append(custom_cat.strip())
                cat_string = " / ".join(all_cats) if all_cats else "Général"
                
                name_lower = name.lower().strip()
                existing_idx = next((i for i, item in enumerate(st.session_state.data_list) if item['Nom du Fournisseur'].lower().strip() == name_lower), None)
                
                if existing_idx is None:
                    new_rec = {"Nom du Fournisseur": name, "Catégories": cat_string, "Téléphone": tel, "Mobile": mob, "Adresse": adr, "E-mail": mail}
                    st.session_state.data_list.append(new_rec)
                else:
                    current = str(st.session_state.data_list[existing_idx]['Catégories'])
                    current_list = [c.strip() for c in current.split('/')]
                    for c in all_cats:
                        if c not in current_list: current = f"{current} / {c}"
                    st.session_state.data_list[existing_idx]['Catégories'] = current
                
                # حفظ الكل
                save_to_cloud(st.session_state.data_list)
                st.success("✅ تم الحفظ والمزامنة مع السحابة")
                st.rerun()

# 5. عرض النتائج
st.divider()
if st.session_state.data_list:
    df_final = pd.DataFrame(st.session_state.data_list)
    st.subheader(f"📋 Liste Unifiée ({len(df_final)} fournisseurs)")
    
    search = st.text_input("🔍 Rechercher (nom, catégorie...) :")
    if search:
        mask = df_final.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        df_final = df_final[mask]

    st.dataframe(df_final, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        out = io.BytesIO()
        df_final.to_excel(out, index=False, engine='openpyxl')
        st.download_button("📥 Exporter Excel", out.getvalue(), "base_fournisseurs.xlsx")
    with col2:
        if st.button("🗑️ Vider la base (Action Irréversible)"):
            if db:
                # حذف من السحابة (للتبسيط نحذف من القائمة ونعيد الكتابة أو نحذف المجموعة)
                docs = db.collection('artifacts', APP_ID, 'public', 'data', 'suppliers').stream()
                for doc in docs: doc.reference.delete()
            st.session_state.data_list = []
            st.rerun()
else:
    st.info("Aucune donnée enregistrée. Importez un fichier pour commencer.")
