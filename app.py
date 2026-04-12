import streamlit as st
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="نظام الموردين الذكي", layout="wide")

# تحسين المظهر ودعم اللغة العربية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Cairo', sans-serif;
        direction: RTL; text-align: right;
    }
    .stDataFrame { direction: RTL; }
    </style>
    """, unsafe_allow_html=True)

# وظيفة الترتيب الذكي المتطور
def smart_clean(df):
    # محرك بحث عن العناوين (فرنسي، إنجليزي، عربي)
    mapping = {
        'N°': 'الرقم',
        'Désignation': 'اسم المورد', 'Designation': 'اسم المورد', 'الشركة': 'اسم المورد',
        'Adresse': 'العنوان', 'Address': 'العنوان', 'العنوان': 'العنوان',
        'Tél': 'الهاتف الثابت', 'Tel': 'الهاتف الثابت', 'Fix': 'الهاتف الثابت',
        'Mobile': 'رقم المحمول', 'الجوّال': 'رقم المحمول', 'Phone': 'رقم المحمول',
        'E-mail': 'البريد الإلكتروني', 'Email': 'البريد الإلكتروني',
        'Fax': 'الفاكس'
    }
    
    # 1. إذا كانت الأعمدة "Unnamed"، نبحث عن أول سطر يحتوي على كلمات مفتاحية
    if "Unnamed" in str(df.columns):
        # البحث عن سطر العناوين الحقيقي في أول 5 صفوف
        for i in range(min(len(df), 5)):
            row_values = df.iloc[i].astype(str).tolist()
            if any(key in str(row_values) for key in mapping.keys()):
                df.columns = df.iloc[i]
                df = df.iloc[i+1:].reset_index(drop=True)
                break

    # 2. إعادة تسمية الأعمدة بناءً على القاموس
    new_cols = {}
    for col in df.columns:
        col_str = str(col).strip()
        for key, val in mapping.items():
            if key.lower() in col_str.lower():
                new_cols[col] = val
                break
    
    df = df.rename(columns=new_cols)
    
    # 3. تنظيف البيانات من الفراغات والقيم الفارغة
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.dropna(how='all')
    return df

st.title("🛡️ بوابة إدارة الموردين الذكية")

# استخدام Session State لحفظ البيانات أثناء الجلسة
if 'main_data' not in st.session_state:
    st.session_state.main_data = pd.DataFrame()

# منطقة الإدخال والرفع
tab1, tab2 = st.tabs(["📥 رفع ملف إكسيل", "➕ إضافة مورد يدوياً"])

with tab1:
    uploaded_file = st.file_uploader("ارفع قائمة الموردين غير المرتبة", type=['xlsx', 'csv'])
    if uploaded_file:
        try:
            raw_df = pd.read_excel(uploaded_file) if uploaded_file.name.endswith('xlsx') else pd.read_csv(uploaded_file)
            if st.button("🪄 ترتيب وحفظ القائمة المرفوعة"):
                cleaned = smart_clean(raw_df)
                st.session_state.main_data = pd.concat([st.session_state.main_data, cleaned], ignore_index=True).drop_duplicates()
                st.success("تم الترتيب والدمج بنجاح!")
        except Exception as e:
            st.error(f"خطأ في قراءة الملف: {e}")

with tab2:
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            m_name = st.text_input("اسم المورد/الشركة")
            m_phone = st.text_input("رقم الهاتف")
        with col2:
            m_cat = st.text_input("العنوان/الولاية")
            m_email = st.text_input("البريد الإلكتروني")
        
        if st.form_submit_button("إضافة إلى القاعدة"):
            new_row = pd.DataFrame([{"اسم المورد": m_name, "رقم المحمول": m_phone, "العنوان": m_cat, "البريد الإلكتروني": m_email}])
            st.session_state.main_data = pd.concat([st.session_state.main_data, new_row], ignore_index=True)
            st.success("تمت الإضافة اليدوية بنجاح!")

# عرض قاعدة البيانات والبحث
st.markdown("---")
if not st.session_state.main_data.empty:
    search = st.text_input("🔍 ابحث في قاعدة البيانات الحالية:")
    display_df = st.session_state.main_data
    
    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # تصدير البيانات نظيفة
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 تحميل قاعدة البيانات كملف CSV نظيف", data=csv, file_name="Suppliers_Database.csv")
else:
    st.info("بانتظار إضافة بيانات أو رفع ملف للبدء.")
