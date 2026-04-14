import streamlit as st
import pandas as pd
import io
import json
from google.cloud import firestore
from google.oauth2 import service_account

# 1. إعدادات الصفحة
st.set_page_config(page_title="نظام إدارة الموردين السحابي", layout="wide", page_icon="🏢")

# تنسيق الواجهة (RTL)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
    .stButton>button { background-color: #10B981; color: white; border-radius: 8px; }
    .stAlert { direction: rtl; }
    </style>
    """, unsafe_allow_html=True)

# 2. ربط قاعدة البيانات السحابية (Firestore)
def init_connection():
    try:
        # البحث عن المفتاح في إعدادات Streamlit Secrets
        if "textkey" in st.secrets:
            key_dict = json.loads(st.secrets["textkey"])
            creds = service_account.Credentials.from_service_account_info(key_dict)
            return firestore.Client(credentials=creds, project=key_dict['project_id'])
    except Exception as e:
        st.sidebar.error(f"⚠️ فشل الاتصال بالسحاب: {e}")
    return None

db = init_connection()
COLLECTION_NAME = "suppliers_data"
DOCUMENT_ID = "main_registry"

# 3. وظائف جلب وحفظ البيانات
def load_data_from_cloud():
    if db:
        try:
            doc_ref = db.collection(COLLECTION_NAME).document(DOCUMENT_ID)
            doc = doc_ref.get()
            if doc.exists:
                return pd.DataFrame(doc.to_dict().get("list", []))
        except Exception as e:
            st.error(f"خطأ أثناء تحميل البيانات: {e}")
    
    # بيانات افتراضية في حال فشل السحاب
    return pd.DataFrame(columns=["اسم المورد", "الفئة", "الشخص المسؤول", "رقم الهاتف", "الحالة"])

def save_data_to_cloud(df):
    if db:
        try:
            doc_ref = db.collection(COLLECTION_NAME).document(DOCUMENT_ID)
            # تحويل DataFrame إلى قائمة قواميس للحفظ
            data_to_save = {"list": df.to_dict('records')}
            doc_ref.set(data_to_save)
            return True
        except Exception as e:
            st.error(f"❌ فشل الحفظ السحابي: {e}")
    return False

# تحميل البيانات في حالة الجلسة
if 'supplier_data' not in st.session_state:
    st.session_state.supplier_data = load_data_from_cloud()

# 4. واجهة المستخدم
st.title("📂 قاعدة بيانات الموردين المركزية")
st.info("💡 يتم مزامنة كافة التعديلات سحابياً لضمان عدم ضياع البيانات.")

# القائمة الجانبية
with st.sidebar:
    st.header("⚙️ العمليات")
    
    if db is None:
        st.warning("⚠️ التطبيق يعمل الآن في 'الوضع المؤقت'. للحفظ الدائم، أضف مفتاح 'textkey' في إعدادات Secrets.")
    else:
        st.success("☁️ الاتصال السحابي نشط")

    # إضافة مورد يدوي
    with st.expander("➕ إضافة مورد جديد"):
        with st.form("add_form", clear_on_submit=True):
            n = st.text_input("اسم المورد *")
            c = st.selectbox("الفئة", ["ميكانيك", "كهرباء", "PPE", "خدمات"])
            p = st.text_input("رقم الهاتف")
            s = st.selectbox("الحالة", ["معتمد", "قيد المراجعة"])
            
            if st.form_submit_button("حفظ"):
                if n:
                    new_row = {"اسم المورد": n, "الفئة": c, "الشخص المسؤول": "", "رقم الهاتف": p, "الحالة": s}
                    st.session_state.supplier_data = pd.concat([st.session_state.supplier_data, pd.DataFrame([new_row])], ignore_index=True)
                    
                    # حفظ فوري في السحاب
                    if save_data_to_cloud(st.session_state.supplier_data):
                        st.success("تم الحفظ في السحاب ✅")
                        st.rerun()
                else:
                    st.error("الاسم مطلوب")

# 5. عرض البيانات والبحث
search = st.text_input("🔍 ابحث عن مورد...")
df_display = st.session_state.supplier_data

if search:
    mask = df_display.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)
    df_display = df_display[mask]

st.dataframe(df_display, use_container_width=True, hide_index=True)

# أزرار التحكم في الأسفل
c1, c2 = st.columns([1, 5])
with c1:
    if st.button("🗑️ مسح الكل"):
        st.session_state.supplier_data = pd.DataFrame(columns=["اسم المورد", "الفئة", "الشخص المسؤول", "رقم الهاتف", "الحالة"])
        save_data_to_cloud(st.session_state.supplier_data)
        st.rerun()

with c2:
    # تصدير Excel
    buffer = io.BytesIO()
    df_display.to_excel(buffer, index=False)
    st.download_button("📥 تحميل كملف Excel", buffer.getvalue(), "suppliers_backup.xlsx")
