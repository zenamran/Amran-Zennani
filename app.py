import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# إعداد الصفحة
st.set_page_config(page_title="قاعدة بيانات المشتريات الذكية", layout="wide")

st.title("🛡️ نظام إدارة الموردين (حفظ دائم + ترتيب ذكي)")

# الاتصال بجوجل شيت (قاعدة البيانات الدائمة)
conn = st.connection("gsheets", type=GSheetsConnection)

# وظيفة الترتيب الذكي (AI Logic)
def smart_clean(df):
    # مصفوفة لتحويل الأسماء العشوائية إلى أسماء قياسية
    mapping = {
        'الشركة': 'اسم المورد', 'المورد': 'اسم المورد', 'Supplier': 'اسم المورد',
        'الهاتف': 'رقم التواصل', 'Phone': 'رقم التواصل', 'Mobile': 'رقم التواصل',
        'النشاط': 'الفئة', 'Category': 'الفئة', 'Type': 'الفئة'
    }
    # إعادة تسمية الأعمدة إذا وجدت في القاموس
    df = df.rename(columns=mapping)
    # تنظيف البيانات من الفراغات
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
    return df

# 1. قراءة البيانات المحفوظة مسبقاً
try:
    existing_data = conn.read(worksheet="Suppliers")
    st.session_state.data = existing_data
except:
    st.session_state.data = pd.DataFrame()

# 2. منطقة رفع الملفات الجديدة (لترتيبها وحفظها)
with st.expander("📥 رفع قائمة جديدة لترتيبها وحفظها"):
    uploaded_file = st.file_uploader("اختر ملف الإكسيل غير المرتب", type=['xlsx', 'csv'])
    if uploaded_file:
        new_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
        
        if st.button("ترتيب البيانات وحفظها نهائياً"):
            cleaned_df = smart_clean(new_df)
            # دمج البيانات الجديدة مع القديمة
            updated_data = pd.concat([st.session_state.data, cleaned_df], ignore_index=True).drop_duplicates()
            # حفظ في جوجل شيت
            conn.update(worksheet="Suppliers", data=updated_data)
            st.success("✅ تم الترتيب والحفظ في قاعدة البيانات الكبرى!")
            st.rerun()

# 3. عرض قاعدة البيانات الكبرى (المحفوظة)
st.markdown("### 📋 قائمة الموردين المسجلين")
if not st.session_state.data.empty:
    search = st.text_input("🔍 ابحث في قاعدة البيانات الكبرى:")
    df_display = st.session_state.data
    if search:
        df_display = df_display[df_display.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
    
    st.dataframe(df_display, use_container_width=True)
else:
    st.warning("قاعدة البيانات فارغة حالياً. قم برفع أول قائمة لتبدأ!")
