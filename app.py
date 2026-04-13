import streamlit as st
import pandas as pd
import io
import json
from firebase_admin import credentials, firestore, initialize_app, _apps

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Système Cloud - Gestion des Fournisseurs",
    page_icon="☁️",
    layout="wide"
)

# تصميم واجهة المستخدم بلمسة احترافية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .main-header { color: #1E40AF; font-weight: bold; border-bottom: 2px solid #1E40AF; padding-bottom: 10px; margin-bottom: 20px; }
    .stAlert { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# 2. تهيئة الاتصال السحابي (Firestore)
def init_db():
    if not _apps:
        try:
            # محاولة جلب إعدادات Firebase من Secrets
            if "firebase" in st.secrets:
                creds_dict = dict(st.secrets["firebase"])
                cred = credentials.Certificate(creds_dict)
                initialize_app(cred)
            else:
                return None
        except Exception:
            return None
    return firestore.client()

db = init_db()
APP_ID = "suppliers_v1" # معرف فريد للتطبيق في السحابة

# وظائف التعامل مع السحابة
def sync_to_cloud(data_list):
    """حفظ البيانات في السحابة"""
    if db:
        for item in data_list:
            # تنظيف الاسم لاستخدامه كمعرف للمستند
            doc_id = item['Nom'].replace("/", "-").strip()
            # المسار المعتمد: /artifacts/{appId}/public/data/{collectionName}
            db.collection('artifacts', APP_ID, 'public', 'data', 'suppliers').document(doc_id).set(item)

def fetch_from_cloud():
    """جلب البيانات من السحابة عند فتح الموقع"""
    if db:
        try:
            docs = db.collection('artifacts', APP_ID, 'public', 'data', 'suppliers').stream()
            return [doc.to_dict() for doc in docs]
        except Exception:
            return []
    return []

# وظيفة لتنظيف البيانات وحل مشكلة (float found)
def safe_str(val):
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def process_excel_sheet(df_raw, sheet_name):
    if df_raw.empty: return []
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    mapping = {
        'Nom': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Tel': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax', 'mobile', 'mob', 'محمول']
    }
    header_row = -1
    col_map = {}
    for i in range(min(20, len(df))):
        row_values = [str(x).lower() for x in df.iloc[i].values]
        temp_map = {}
        matches = 0
        for target, keys in mapping.items():
            for idx, cell in enumerate(row_values):
                if any(k in cell for k in keys):
                    temp_map[target] = idx
                    matches += 1
                    break
        if matches >= 1:
            header_row, col_map = i, temp_map
            break
            
    extracted = []
    if header_row != -1:
        data_part = df.iloc[header_row + 1:]
        for _, row in data_part.iterrows():
            name = safe_str(row.iloc[col_map['Nom']]) if 'Nom' in col_map else safe_str(row.iloc[0])
            if name and name.lower() not in ['nom', 'fournisseur', 'designation', 'اسم', '']:
                entry = {
                    "Nom": name,
                    "Catégories": str(sheet_name),
                    "Adresse": safe_str(row.iloc[col_map['Adresse']]) if 'Adresse' in col_map else "",
                    "Contact": safe_str(row.iloc[col_map['Tel']]) if 'Tel' in col_map else ""
                }
                extracted.append(entry)
    return extracted

# 3. إدارة حالة التطبيق
if 'suppliers_db' not in st.session_state:
    # تحميل البيانات من السحابة فور فتح الموقع
    cloud_data = fetch_from_cloud()
    st.session_state.suppliers_db = cloud_data if cloud_data else []

st.markdown("<h1 class='main-header'>☁️ منصة إدارة الموردين السحابية</h1>", unsafe_allow_html=True)

if not db:
    st.info("💡 ملاحظة: التطبيق يعمل حالياً في وضع الذاكرة. لتفعيل الحفظ السحابي الدائم، يرجى إعداد مفاتيح Firebase Secrets.")

menu = ["📋 عرض قاعدة البيانات", "📂 استيراد ملف جديد", "➕ إضافة مورد يدوي"]
choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

if choice == "📂 استيراد ملف جديد":
    st.subheader("رفع ملفات Excel للمزامنة")
    file = st.file_uploader("اختر ملف .xlsx", type="xlsx")
    
    if file:
        xl = pd.ExcelFile(file)
        selected_sheets = st.multiselect("اختر التخصصات (الأوراق):", xl.sheet_names, default=xl.sheet_names)
        
        if st.button("🚀 معالجة وحفظ في السحابة"):
            new_records = 0
            for sheet in selected_sheets:
                df_sheet = pd.read_excel(file, sheet_name=sheet, header=None)
                results = process_excel_sheet(df_sheet, sheet)
                for item in results:
                    existing = next((x for x in st.session_state.suppliers_db if x['Nom'].lower() == item['Nom'].lower()), None)
                    if existing:
                        if item['Catégories'] not in existing['Catégories']:
                            existing['Catégories'] += f" / {item['Catégories']}"
                    else:
                        st.session_state.suppliers_db.append(item)
                        new_records += 1
            
            # مزامنة كل البيانات مع السحابة
            sync_to_cloud(st.session_state.suppliers_db)
            st.success(f"✅ تمت المزامنة! تم إضافة {new_records} مورد جديد.")

elif choice == "➕ إضافة مورد يدوي":
    st.subheader("إضافة مورد للقاعدة السحابية")
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("اسم الشركة *")
            cats = st.text_input("التخصصات")
        with col2:
            contact = st.text_input("الاتصال")
            address = st.text_area("العنوان")
            
        if st.form_submit_button("💾 حفظ دائم"):
            if name:
                existing = next((x for x in st.session_state.suppliers_db if x['Nom'].lower() == name.lower()), None)
                if existing:
                    existing['Catégories'] += f" / {cats}"
                else:
                    st.session_state.suppliers_db.append({"Nom": name, "Catégories": cats, "Contact": contact, "Adresse": address})
                
                sync_to_cloud(st.session_state.suppliers_db)
                st.success("✅ تم الحفظ في السحابة بنجاح.")
            else:
                st.error("الاسم مطلوب!")

elif choice == "📋 عرض قاعدة البيانات":
    st.subheader("الموردون المحفوظون سحابياً")
    
    if st.session_state.suppliers_db:
        df_display = pd.DataFrame(st.session_state.suppliers_db)
        search = st.text_input("🔍 بحث فوري في القاعدة:")
        if search:
            df_display = df_display[df_display.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
            
        st.dataframe(df_display, use_container_width=True, hide_index=True)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_display.to_excel(writer, index=False)
            st.download_button("📥 تحميل نسخة Excel", buffer.getvalue(), "cloud_backup.xlsx")
        with col2:
            if st.button("🗑️ مسح السحابة (نهائي)"):
                if db:
                    docs = db.collection('artifacts', APP_ID, 'public', 'data', 'suppliers').stream()
                    for doc in docs: doc.reference.delete()
                st.session_state.suppliers_db = []
                st.rerun()
    else:
        st.warning("لا توجد بيانات محفوظة. ابدأ بالرفع أو الإضافة.")
