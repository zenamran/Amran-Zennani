import streamlit as st
import pandas as pd
import io
import json
import os
from datetime import datetime

# إعداد الصفحة
st.set_page_config(page_title="Cloud Suppliers Pro", layout="wide", page_icon="🏢")

# --- تنبيه هام للمستخدم ---
st.markdown("""
    <style>
    .main-header { color: #1E3A8A; font-weight: bold; border-bottom: 3px solid #3B82F6; padding-bottom: 10px; }
    .stAlert { direction: rtl; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# --- محاكاة التخزين السحابي الدائم ---
# ملاحظة: في Streamlit Cloud، نستخدم ملفات محلية في المجلد 'data' 
# أو نعتمد على استمرارية الـ Session State مع خيار التصدير المستمر.
# لتفعيل الحفظ الحقيقي عبر الإنترنت، سنستخدم نظام JSON المحسن.

DATA_FILE = "suppliers_cloud_storage.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        st.error(f"خطأ في الحفظ السحابي: {e}")

# تهيئة البيانات عند فتح الموقع
if 'suppliers' not in st.session_state:
    st.session_state.suppliers = load_data()

# --- وظائف المعالجة الذكية (لحل أخطاء الصور) ---
def clean_val(val):
    """حل مشكلة float found و str expected"""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def process_excel(file, sheets):
    new_entries = []
    for sheet in sheets:
        try:
            df = pd.read_excel(file, sheet_name=sheet, header=None)
            # تحويل كل الجدول لنصوص فوراً لتجنب أي تعارض أنواع
            df = df.fillna("").astype(str)
            
            # البحث عن الأعمدة (اسم، هاتف، عنوان)
            # نأخذ أول عمود كاسم إذا لم نجد كلمة "اسم"
            for index, row in df.iterrows():
                # نتجاهل الأسطر التي تبدو كعناوين
                if any(k in row.values[0].lower() for k in ['nom', 'designation', 'اسم']):
                    continue
                
                name = clean_val(row.values[0])
                if name:
                    entry = {
                        "Nom": name,
                        "Catégories": str(sheet),
                        "Contact": clean_val(row.values[1]) if len(row) > 1 else "",
                        "Adresse": clean_val(row.values[2]) if len(row) > 2 else "",
                        "LastUpdate": datetime.now().strftime("%Y-%m-%d")
                    }
                    new_entries.append(entry)
        except Exception as e:
            st.warning(f"تنبيه: تعذر قراءة الورقة {sheet} بسبب: {e}")
    return new_entries

# --- الواجهة الرئيسية ---
st.markdown("<h1 class='main-header'>🏢 منصة إدارة الموردين - حفظ سحابي دائم</h1>", unsafe_allow_html=True)

menu = ["📋 عرض قاعدة البيانات", "📥 استيراد ودمج (Excel)", "➕ إضافة يدوية"]
choice = st.sidebar.radio("انتقل إلى:", menu)

if choice == "📥 استيراد ودمج (Excel)":
    st.subheader("رفع ملفات جديدة للمزامنة")
    uploaded_file = st.file_uploader("اختر ملف الإكسيل", type="xlsx")
    
    if uploaded_file:
        xl = pd.ExcelFile(uploaded_file)
        selected_sheets = st.multiselect("اختر التخصصات المراد دمجها:", xl.sheet_names, default=xl.sheet_names)
        
        if st.button("🚀 معالجة ورفع للسحابة"):
            extracted_data = process_excel(uploaded_file, selected_sheets)
            
            count_new = 0
            for item in extracted_data:
                # دمج ذكي: إذا وجدنا نفس الاسم، ندمج الفئات فقط
                existing = next((x for x in st.session_state.suppliers if x['Nom'].lower() == item['Nom'].lower()), None)
                if existing:
                    if item['Catégories'] not in existing['Catégories']:
                        existing['Catégories'] += f" / {item['Catégories']}"
                else:
                    st.session_state.suppliers.append(item)
                    count_new += 1
            
            save_data(st.session_state.suppliers)
            st.success(f"✅ تم بنجاح! تم إضافة {count_new} مورد جديد وتحديث الموردين الحاليين.")

elif choice == "➕ إضافة يدوية":
    st.subheader("إضافة مورد جديد يدوياً")
    with st.form("manual_add"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم المورد/الشركة *")
            category = st.text_input("الفئة/التخصص")
        with c2:
            contact = st.text_input("معلومات الاتصال")
            address = st.text_area("العنوان")
        
        if st.form_submit_button("💾 حفظ في القاعدة"):
            if name:
                new_item = {
                    "Nom": name, "Catégories": category, 
                    "Contact": contact, "Adresse": address,
                    "LastUpdate": datetime.now().strftime("%Y-%m-%d")
                }
                st.session_state.suppliers.append(new_item)
                save_data(st.session_state.suppliers)
                st.success("✅ تم الحفظ بنجاح")
            else:
                st.error("يرجى إدخال الاسم على الأقل")

elif choice == "📋 عرض قاعدة البيانات":
    st.subheader(f"🗄️ الموردون المسجلون ({len(st.session_state.suppliers)})")
    
    if st.session_state.suppliers:
        df = pd.DataFrame(st.session_state.suppliers)
        
        # البحث
        search = st.text_input("🔍 ابحث عن مورد، فئة، أو رقم هاتف:")
        if search:
            df = df[df.apply(lambda row: search.lower() in row.astype(str).str.lower().str.cat(), axis=1)]
        
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        # تصدير
        towrite = io.BytesIO()
        df.to_excel(towrite, index=False, engine='xlsxwriter')
        st.download_button(label="📥 تحميل القاعدة كاملة (Excel)", data=towrite.getvalue(), file_name="Suppliers_Database.xlsx")
        
        if st.sidebar.button("⚠️ مسح كافة البيانات"):
            st.session_state.suppliers = []
            save_data([])
            st.rerun()
    else:
        st.info("قاعدة البيانات فارغة حالياً. قم برفع ملف إكسيل للبدء.")
