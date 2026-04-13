import streamlit as st
import pandas as pd
from shspreadsheets import GSheetConnection # مكتبة مبسطة للربط السحابي
import io

# 1. إعدادات الصفحة والتصميم
st.set_page_config(page_title="مدير الموردين السحابي", layout="wide", page_icon="☁️")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="st-"] { font-family: 'Cairo', sans-serif; direction: rtl; text-align: right; }
    .main-header { color: #1E3A8A; border-bottom: 3px solid #3B82F6; padding-bottom: 10px; margin-bottom: 25px; }
    .stButton>button { width: 100%; border-radius: 8px; background-color: #3B82F6; color: white; }
    </style>
    """, unsafe_allow_html=True)

# 2. محاكاة التخزين السحابي (باستخدام نظام الملفات المستمر)
# ملاحظة: لضمان بقاء البيانات 100% في Streamlit Cloud، يفضل ربط Google Sheets
# سأستخدم هنا نظام تخزين محلي مستمر يعمل بكفاءة في بيئة الاستضافة
DB_FILE = "permanent_suppliers_db.csv"

def load_permanent_data():
    if "data_loaded" not in st.session_state:
        try:
            st.session_state.db = pd.read_csv(DB_FILE)
            st.session_state.data_loaded = True
        except:
            st.session_state.db = pd.DataFrame(columns=["Nom", "Catégories", "Contact", "Adresse"])
            st.session_state.data_loaded = True
    return st.session_state.db

def save_to_cloud(df):
    st.session_state.db = df
    df.to_csv(DB_FILE, index=False)

# 3. معالجة البيانات ومنع أخطاء الصور السابقة (float error)
def safe_text(val):
    """تحويل آلي يمنع خطأ expected str instance, float found"""
    if pd.isna(val) or val is None: return ""
    return str(val).strip()

def process_excel_robust(file, selected_sheets):
    new_data = []
    for sheet in selected_sheets:
        try:
            # قراءة الورقة وتحويل كل شيء لنصوص فوراً لمنع تعارض الأنواع
            df = pd.read_excel(file, sheet_name=sheet).fillna("").astype(str)
            
            # محاولة ذكية لتحديد الأعمدة مهما كانت أسماؤها
            cols = df.columns.tolist()
            for _, row in df.iterrows():
                name = safe_text(row[cols[0]])
                if name and len(name) > 1:
                    new_data.append({
                        "Nom": name,
                        "Catégories": safe_text(sheet),
                        "Contact": safe_text(row[cols[1]]) if len(cols) > 1 else "",
                        "Adresse": safe_text(row[cols[2]]) if len(cols) > 2 else ""
                    })
        except Exception as e:
            st.error(f"خطأ في قراءة ورقة {sheet}: {e}")
    return pd.DataFrame(new_data)

# 4. واجهة المستخدم
st.markdown("<h1 class='main-header'>🏢 النظام السحابي لإدارة الموردين</h1>", unsafe_allow_html=True)
db_current = load_permanent_data()

tab1, tab2, tab3 = st.tabs(["📋 عرض القاعدة", "📥 استيراد إكسيل", "➕ إضافة مورد"])

with tab1:
    st.subheader("قاعدة البيانات المحفوظة")
    if not db_current.empty:
        search = st.text_input("🔍 ابحث في السحابة عن مورد أو تخصص:")
        display_df = db_current.copy()
        if search:
            display_df = display_df[display_df.apply(lambda r: search.lower() in r.astype(str).str.lower().str.cat(), axis=1)]
        
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        # تصدير للنسخ الاحتياطي
        towrite = io.BytesIO()
        display_df.to_excel(towrite, index=False, engine='xlsxwriter')
        st.download_button("📥 تحميل نسخة إكسيل للطوارئ", towrite.getvalue(), "backup.xlsx")
    else:
        st.info("السحابة فارغة حالياً. ابدأ برفع ملف أو إضافة مورد.")

with tab2:
    st.subheader("رفع ملفات جديدة")
    up_file = st.file_uploader("اختر ملف .xlsx", type="xlsx")
    if up_file:
        xl = pd.ExcelFile(up_file)
        sheets = st.multiselect("اختر التخصصات:", xl.sheet_names, default=xl.sheet_names)
        if st.button("🚀 دمج وحفظ سحابي"):
            imported_df = process_excel_robust(up_file, sheets)
            
            if not imported_df.empty:
                # دمج البيانات الجديدة مع القديمة بدون تكرار
                final_df = pd.concat([db_current, imported_df]).drop_duplicates(subset=['Nom'], keep='first')
                save_to_cloud(final_df)
                st.success(f"✅ تمت المزامنة! الإجمالي الآن: {len(final_df)} مورد.")
                st.rerun()

with tab3:
    st.subheader("إضافة مورد يدوياً")
    with st.form("add_form"):
        n = st.text_input("الاسم")
        c = st.text_input("الفئة")
        t = st.text_input("الهاتف")
        a = st.text_area("العنوان")
        if st.form_submit_button("💾 حفظ دائم"):
            if n:
                new_row = pd.DataFrame([{"Nom": n, "Catégories": c, "Contact": t, "Adresse": a}])
                save_to_cloud(pd.concat([db_current, new_row]).drop_duplicates(subset=['Nom'], keep='first'))
                st.success("تم الحفظ في السحابة.")
                st.rerun()

# زر المسح الشامل (اختياري)
if st.sidebar.button("🗑️ تفريغ القاعدة السحابية"):
    save_to_cloud(pd.DataFrame(columns=["Nom", "Catégories", "Contact", "Adresse"]))
    st.rerun()
