import streamlit as st
import pandas as pd
import io

# إعدادات الصفحة الأساسية
st.set_page_config(page_title="نظام إدارة الموردين الاحترافي", layout="wide")

# تطبيق التصميم العربي المتوافق
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: RTL; text-align: right;
    }
    .stDataFrame { direction: RTL; }
    .stAlert { direction: RTL; text-align: right; }
    /* تحسين شكل التبويبات العلوية */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    </style>
    """, unsafe_allow_html=True)

def robust_clean(df):
    """دالة تنظيف فائقة القوة للتعامل مع كافة أنواع البيانات"""
    if df.empty:
        return df

    # قاموس العناوين الذكي المحدث ليشمل اسم الشركة
    mapping = {
        'désignation': 'اسم الشركة/المورد', 'الشركة': 'اسم الشركة/المورد', 'nom': 'اسم الشركة/المورد',
        'adresse': 'العنوان', 'address': 'العنوان',
        'tél': 'الهاتف', 'tel': 'الهاتف', 'phone': 'الهاتف',
        'mobile': 'رقم المحمول', 'mob': 'رقم المحمول',
        'email': 'البريد الإلكتروني', 'e-mail': 'البريد الإلكتروني',
        'fax': 'الفاكس'
    }

    # 1. البحث عن سطر الرأس (Header)
    actual_header_index = 0
    found = False
    for i in range(min(len(df), 20)):
        row_values = [str(val).lower() for val in df.iloc[i].values if pd.notna(val)]
        if any(key in " ".join(row_values) for key in mapping.keys()):
            actual_header_index = i
            found = True
            break
    
    if found:
        df.columns = df.iloc[actual_header_index]
        df = df.iloc[actual_header_index + 1:].reset_index(drop=True)

    # 2. توحيد أسماء الأعمدة وتنظيفها
    df.columns = [str(c).strip() if pd.notna(c) else f"Column_{i}" for i, c in enumerate(df.columns)]
    
    new_cols = {}
    for col in df.columns:
        for key, val in mapping.items():
            if key.lower() in col.lower():
                new_cols[col] = val
                break
    
    df = df.rename(columns=new_cols)

    # 3. تنظيف البيانات
    def clean_cell(x):
        if pd.isna(x): return ""
        return str(x).strip()

    df = df.map(clean_cell)
    
    # 4. تصفية الأعمدة غير المرغوب فيها (الإبقاء على المعرف منها فقط)
    important_cols = list(set(mapping.values()))
    existing_important = [c for c in important_cols if c in df.columns]
    
    if existing_important:
        df = df[existing_important]

    # 5. حذف الصفوف الفارغة تماماً
    df = df.replace("", pd.NA).dropna(how='all').reset_index(drop=True)
    
    return df

st.title("🛡️ بوابة الموردين الذكية (الإصدار المستقر)")

if 'final_db' not in st.session_state:
    st.session_state.final_db = pd.DataFrame()

# تقسيم الواجهة إلى تبويبات
tab_upload, tab_manual = st.tabs(["📥 رفع ومعالجة الملفات", "➕ إضافة مورد يدوياً"])

with tab_upload:
    # منطقة رفع الملفات
    with st.sidebar:
        st.header("⚙️ الإعدادات")
        uploaded_file = st.file_uploader("ارفع ملف الإكسيل الرئيسي", type=['xlsx'])
        
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            all_sheets = xl.sheet_names
            
            st.info(f"📁 تم اكتشاف {len(all_sheets)} فئات (صفحات) في الملف.")
            
            # اختيار الصفحات
            selected = st.multiselect("اختر الأقسام التي تريد دمجها:", all_sheets, default=all_sheets)
            
            if st.button("🚀 معالجة ودمج كافة البيانات"):
                combined_data = []
                progress_bar = st.progress(0)
                
                for index, sheet in enumerate(selected):
                    try:
                        df_raw = pd.read_excel(uploaded_file, sheet_name=sheet)
                        cleaned = robust_clean(df_raw)
                        if not cleaned.empty:
                            cleaned['القسم'] = sheet
                            combined_data.append(cleaned)
                    except Exception as e:
                        st.error(f"خطأ في صفحة {sheet}: {str(e)}")
                    progress_bar.progress((index + 1) / len(selected))
                
                if combined_data:
                    # دمج الجداول
                    st.session_state.final_db = pd.concat(combined_data, axis=0, ignore_index=True, sort=False)
                    st.success("✨ تم بناء قاعدة البيانات الموحدة بنجاح!")
                else:
                    st.warning("لم يتم العثور على بيانات صالحة في الصفحات المختارة.")

        except Exception as e:
            st.error(f"فشل في فتح الملف: {str(e)}")

with tab_manual:
    st.header("إضافة مورد جديد يدوياً")
    with st.form("manual_entry_form"):
        col1, col2 = st.columns(2)
        with col1:
            m_company = st.text_input("اسم الشركة/المورد *")
            m_phone = st.text_input("رقم الهاتف")
            m_mobile = st.text_input("رقم المحمول")
        with col2:
            m_category = st.text_input("القسم/الفئة")
            m_address = st.text_input("العنوان")
            m_email = st.text_input("البريد الإلكتروني")
        
        submitted = st.form_submit_button("حفظ المورد في القائمة")
        
        if submitted:
            if m_company:
                new_row = pd.DataFrame([{
                    "اسم الشركة/المورد": m_company,
                    "الهاتف": m_phone,
                    "رقم المحمول": m_mobile,
                    "العنوان": m_address,
                    "البريد الإلكتروني": m_email,
                    "القسم": m_category
                }])
                st.session_state.final_db = pd.concat([st.session_state.final_db, new_row], ignore_index=True)
                st.success(f"✅ تم إضافة المورد '{m_company}' بنجاح!")
            else:
                st.error("يرجى إدخال اسم الشركة على الأقل.")

# عرض قاعدة البيانات والبحث والتحميل
if not st.session_state.final_db.empty:
    st.markdown("---")
    
    # محرك بحث ذكي
    search_query = st.text_input("🔍 ابحث عن مورد، هاتف، أو فئة:", placeholder="اكتب هنا للبحث...")
    
    df_to_show = st.session_state.final_db
    if search_query:
        mask = df_to_show.astype(str).apply(lambda x: x.str.contains(search_query, case=False, na=False)).any(axis=1)
        df_to_show = df_to_show[mask]

    st.write(f"📊 تم العثور على **{len(df_to_show)}** مورد.")
    st.dataframe(df_to_show, use_container_width=True, hide_index=True)

    # تصدير البيانات
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
        df_to_show.to_excel(writer, index=False, sheet_name='Database')
    
    st.download_button(
        label="📥 تحميل قاعدة البيانات الموحدة (Excel)",
        data=buffer.getvalue(),
        file_name="Final_Suppliers_Database.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
else:
    if not uploaded_file:
        st.info("قم برفع ملف الإكسيل أو استخدم تبويب الإضافة اليدوية للبدء.")
