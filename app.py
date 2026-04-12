import streamlit as st
import pandas as pd

# إعدادات الصفحة
st.set_page_config(page_title="نظام إدارة الموردين الاحترافي", layout="wide")

# تصميم الواجهة ودعم اللغة العربية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Cairo', sans-serif;
        direction: RTL; text-align: right;
    }
    .stDataFrame { direction: RTL; }
    div[data-testid="stExpander"] { text-align: right; }
    </style>
    """, unsafe_allow_html=True)

def smart_clean(df):
    """وظيفة ذكية لتنظيف وترتيب بيانات الإكسيل مهما كان شكلها"""
    if df.empty:
        return df

    # قاموس المصطلحات للبحث عن العناوين (فرنسي، إنجليزي، عربي)
    mapping = {
        'N°': 'الرقم',
        'Désignation': 'اسم المورد', 'Designation': 'اسم المورد',
        'Adresse': 'العنوان', 'Address': 'العنوان',
        'Tél': 'الهاتف', 'Tel': 'الهاتف', 'Tél/Mob': 'الهاتف',
        'Mobile': 'رقم المحمول', 'Mob': 'رقم المحمول',
        'E-mail': 'البريد الإلكتروني', 'Email': 'البريد الإلكتروني',
        'Fax': 'الفاكس'
    }
    
    # 1. محاولة العثور على سطر الرأس الحقيقي
    found_header = False
    for i in range(min(len(df), 15)):
        row_str = " ".join(df.iloc[i].astype(str).tolist()).lower()
        if any(key.lower() in row_str for key in ['désignation', 'tél', 'adresse']):
            df.columns = df.iloc[i]
            df = df.iloc[i+1:].reset_index(drop=True)
            found_header = True
            break
            
    # 2. تنظيف أسماء الأعمدة من الفراغات والقيم غير النصية
    df.columns = [str(c).strip() for c in df.columns]
    
    # 3. إعادة تسمية الأعمدة بناءً على القاموس
    rename_dict = {}
    for col in df.columns:
        for key, val in mapping.items():
            if key.lower() in col.lower():
                rename_dict[col] = val
                break
    
    df = df.rename(columns=rename_dict)
    
    # 4. إبقاء الأعمدة التي تم التعرف عليها فقط لتوحيد الجداول
    valid_cols = [v for v in mapping.values() if v in df.columns]
    if valid_cols:
        df = df[valid_cols]
    
    # 5. تنظيف البيانات من الفراغات وحذف الصفوف الفارغة
    df = df.map(lambda x: str(x).strip() if not pd.isna(x) else "")
    df = df.replace(["nan", "None", ""], pd.NA).dropna(how='all')
    
    return df

st.title("🛡️ بوابة الموردين الذكية - دمج الصفحات")

# استخدام Session State لتخزين البيانات لتبقى ثابتة أثناء التنقل
if 'all_data' not in st.session_state:
    st.session_state.all_data = pd.DataFrame()

uploaded_file = st.file_uploader("ارفع ملف الإكسيل (xlsx)", type=['xlsx'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        sheet_names = xl.sheet_names
        
        st.sidebar.markdown("### 📄 صفحات الملف المكتشفة")
        selected_sheets = st.sidebar.multiselect("اختر الصفحات للدمج:", sheet_names, default=sheet_names)
        
        if st.button("🪄 دمج وتنظيم الصفحات المختارة"):
            combined_list = []
            for sheet in selected_sheets:
                try:
                    df_raw = pd.read_excel(uploaded_file, sheet_name=sheet)
                    cleaned = smart_clean(df_raw)
                    if not cleaned.empty:
                        cleaned['التصنيف (الصفحة)'] = sheet
                        combined_list.append(cleaned)
                except Exception as e:
                    st.warning(f"تعذر معالجة صفحة {sheet}: {e}")
            
            if combined_list:
                # دمج الجداول مع ضمان عدم وجود أخطاء في الفهارس
                st.session_state.all_data = pd.concat(combined_list, axis=0, ignore_index=True)
                # حذف الأعمدة المكررة تماماً إن وجدت
                st.session_state.all_data = st.session_state.all_data.loc[:, ~st.session_state.all_data.columns.duplicated()]
                st.success(f"✅ تم بنجاح دمج {len(combined_list)} صفحة!")
            else:
                st.error("لم يتم العثور على بيانات صالحة في الصفحات المختارة.")
                
    except Exception as e:
        st.error(f"خطأ في قراءة الملف: {e}")

# عرض البيانات والبحث والتحميل
if not st.session_state.all_data.empty:
    st.markdown("---")
    col_search, col_stats = st.columns([3, 1])
    with col_search:
        search_term = st.text_input("🔍 ابحث عن مورد، مدينة، أو رقم هاتف:")
    with col_stats:
        st.metric("إجمالي الموردين", len(st.session_state.all_data))

    display_df = st.session_state.all_data
    if search_term:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]

    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # زر التحميل
    csv_data = display_df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 تحميل قاعدة البيانات الموحدة (Excel CSV)",
        data=csv_data,
        file_name="Global_Suppliers_Database.csv",
        mime='text/csv'
    )
else:
    st.info("قم برفع ملف الإكسيل واختيار الصفحات لبناء قاعدة البيانات.")
