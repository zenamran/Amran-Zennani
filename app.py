import streamlit as st
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="نظام الموردين الشامل", layout="wide")

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

def smart_clean(df):
    mapping = {
        'N°': 'الرقم',
        'Désignation': 'اسم المورد', 'Designation': 'اسم المورد',
        'Adresse': 'العنوان', 'Address': 'العنوان',
        'Tél': 'الهاتف', 'Tel': 'الهاتف', 'Tél/Mob': 'الهاتف',
        'Mobile': 'رقم المحمول', 'Mob': 'رقم المحمول',
        'E-mail': 'البريد الإلكتروني', 'Email': 'البريد الإلكتروني',
        'Fax': 'الفاكس'
    }
    
    # محاولة العثور على رأس الجدول إذا كان هناك صفوف فارغة
    for i in range(min(len(df), 10)):
        row = df.iloc[i].astype(str).tolist()
        if any(str(k).lower() in str(row).lower() for k in mapping.keys()):
            df.columns = df.iloc[i]
            df = df.iloc[i+1:].reset_index(drop=True)
            break

    # إعادة تسمية الأعمدة
    new_cols = {}
    for col in df.columns:
        c = str(col).strip()
        for k, v in mapping.items():
            if k.lower() in c.lower():
                new_cols[col] = v
                break
    df = df.rename(columns=new_cols)
    
    # تنظيف البيانات
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    df = df.dropna(subset=[df.columns[1]]) if len(df.columns) > 1 else df.dropna(how='all')
    return df

st.title("🛡️ بوابة الموردين الذكية (دعم جميع الصفحات)")

if 'main_data' not in st.session_state:
    st.session_state.main_data = pd.DataFrame()

uploaded_file = st.file_uploader("ارفع ملف الإكسيل الذي يحتوي على صفحات متعددة", type=['xlsx'])

if uploaded_file:
    # قراءة أسماء جميع الصفحات في الملف
    xl = pd.ExcelFile(uploaded_file)
    sheet_names = xl.sheet_names
    
    st.write(f"📂 تم العثور على {len(sheet_names)} صفحات في الملف.")
    
    # خيار لاختيار صفحات محددة أو دمج الكل
    selected_sheets = st.multiselect("اختر الصفحات التي تريد استيرادها:", sheet_names, default=sheet_names)
    
    if st.button("🪄 معالجة ودمج الصفحات المختارة"):
        all_sheets_df = []
        for sheet in selected_sheets:
            df_sheet = pd.read_excel(uploaded_file, sheet_name=sheet)
            cleaned_sheet = smart_clean(df_sheet)
            cleaned_sheet['المصدر (الصفحة)'] = sheet # إضافة عمود لمعرفة مصدر البيانات
            all_sheets_df.append(cleaned_sheet)
        
        if all_sheets_df:
            st.session_state.main_data = pd.concat(all_sheets_df, ignore_index=True).drop_duplicates()
            st.success(f"✅ تم دمج {len(selected_sheets)} صفحات بنجاح!")

# إضافة مورد يدوياً
with st.expander("➕ إضافة مورد جديد يدوياً إلى القائمة"):
    with st.form("manual_entry"):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("اسم المورد")
            phone = st.text_input("الهاتف/المحمول")
        with c2:
            addr = st.text_input("العنوان")
            email = st.text_input("البريد الإلكتروني")
        
        if st.form_submit_button("إضافة الآن"):
            new_data = pd.DataFrame([{"اسم المورد": name, "الهاتف": phone, "العنوان": addr, "البريد الإلكتروني": email, "المصدر (الصفحة)": "إدخال يدوي"}])
            st.session_state.main_data = pd.concat([st.session_state.main_data, new_data], ignore_index=True)
            st.success("تمت الإضافة!")

# عرض النتائج والبحث
st.markdown("---")
if not st.session_state.main_data.empty:
    search = st.text_input("🔍 ابحث في جميع الموردين (من كافة الصفحات):")
    display_df = st.session_state.main_data
    
    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]
    
    st.write(f"عرض `{len(display_df)}` مورد.")
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    csv = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 تحميل قاعدة البيانات الموحدة (CSV)", data=csv, file_name="All_Suppliers_Combined.csv")
else:
    st.info("قم برفع ملف الإكسيل للبدء في دمج الصفحات.")
