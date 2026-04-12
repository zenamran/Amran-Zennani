import streamlit as st
import pandas as pd
import io

# إعدادات الصفحة
st.set_page_config(page_title="نظام إدارة الموردين الاحترافي", layout="wide")

# تصميم الواجهة ودعم اللغة العربية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Cairo', sans-serif;
        direction: RTL; text-align: right;
    }
    .stDataFrame { direction: RTL; }
    .stAlert { direction: RTL; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

def robust_clean(df):
    """نسخة محسنة لضمان استخراج اسم المورد بدقة"""
    if df.empty:
        return df

    # تحويل كافة العناوين إلى نصوص لتجنب أخطاء النوع
    df.columns = [str(c).strip() for c in df.columns]

    # قاموس العناوين الذكي (تمت إضافة مرادفات أكثر)
    mapping = {
        'اسم المورد': ['اسم المورد', 'اسم الشركة', 'désignation', 'designation', 'nom', 'name', 'fournisseur', 'société'],
        'العنوان': ['عنوان', 'adresse', 'address', 'lieu', 'wilaya'],
        'الهاتف': ['هاتف', 'tél', 'tel', 'phone', 'fixe'],
        'رقم المحمول': ['محمول', 'جوّال', 'mobile', 'mob', 'tél/mob'],
        'البريد الإلكتروني': ['بريد', 'إيميل', 'email', 'e-mail', 'mail'],
        'الفاكس': ['فاكس', 'fax']
    }

    # 1. محاولة العثور على سطر الرأس (Header)
    header_idx = 0
    found_header = False
    for i in range(min(len(df), 20)):
        row_str = " ".join(df.iloc[i].astype(str).tolist()).lower()
        # إذا وجدنا أي كلمة تدل على "اسم المورد" أو "الهاتف" نعتبر هذا هو الرأس
        if any(keyword in row_str for keyword in ['désign', 'design', 'nom', 'tél', 'tel', 'اسم']):
            header_idx = i
            found_header = True
            break
    
    if found_header:
        df.columns = [str(c).strip() for c in df.iloc[header_idx]]
        df = df.iloc[header_idx + 1:].reset_index(drop=True)

    # 2. إعادة تسمية الأعمدة بناءً على البحث عن الكلمات المفتاحية داخل اسم العمود
    new_columns = {}
    for col in df.columns:
        col_lower = str(col).lower()
        for standard_name, keywords in mapping.items():
            if any(key in col_lower for key in keywords):
                new_columns[col] = standard_name
                break
    
    # 3. معالجة خاصة: إذا لم يتم العثور على "اسم المورد"، نعتبر أول عمود نصي هو الاسم
    df = df.rename(columns=new_columns)
    if 'اسم المورد' not in df.columns:
        # البحث عن أول عمود لا يسمى "الرقم" أو "N°" ونسميه اسم المورد
        potential_cols = [c for c in df.columns if 'n°' not in str(c).lower() and 'رقم' not in str(c).lower()]
        if potential_cols:
            df = df.rename(columns={potential_cols[0]: 'اسم المورد'})

    # 4. تنظيف الخلايا (إصلاح مشكلة float/str)
    def clean_val(val):
        if pd.isna(val) or str(val).lower() in ['nan', 'none', 'null']:
            return ""
        return str(val).strip()

    df = df.map(clean_val)

    # 5. اختيار الأعمدة الهامة فقط (التي تم التعرف عليها)
    final_cols = [v for v in mapping.keys() if v in df.columns]
    if final_cols:
        df = df[final_cols]
    
    # 6. إزالة الصفوف التي لا تحتوي على اسم مورد (لأنها قد تكون صفوف فارغة أو تذييل صفحة)
    if 'اسم المورد' in df.columns:
        df = df[df['اسم المورد'] != ""]
    
    return df.reset_index(drop=True)

st.title("🛡️ بوابة الموردين الذكية - الإصدار المحدث")

if 'full_database' not in st.session_state:
    st.session_state.full_database = pd.DataFrame()

with st.sidebar:
    st.header("📂 تحميل البيانات")
    uploaded_file = st.file_uploader("ارفع ملف الموردين (Excel)", type=['xlsx'])

if uploaded_file:
    try:
        xl = pd.ExcelFile(uploaded_file)
        sheets = xl.sheet_names
        st.success(f"تم العثور على {len(sheets)} أقسام.")
        
        selected_sheets = st.multiselect("اختر الأقسام للاستيراد:", sheets, default=sheets)
        
        if st.button("🚀 معالجة ودمج الموردين"):
            all_dfs = []
            progress = st.progress(0)
            
            for i, sheet in enumerate(selected_sheets):
                df_raw = pd.read_excel(uploaded_file, sheet_name=sheet)
                cleaned = robust_clean(df_raw)
                if not cleaned.empty:
                    cleaned['الفئة (القسم)'] = sheet
                    all_dfs.append(cleaned)
                progress.progress((i + 1) / len(selected_sheets))
            
            if all_dfs:
                st.session_state.full_database = pd.concat(all_dfs, axis=0, ignore_index=True, sort=False)
                st.success(f"تم بنجاح دمج {len(st.session_state.full_database)} مورد!")
            else:
                st.error("لم يتم العثور على بيانات 'اسم المورد' في الصفحات المختارة. تأكد من جودة الملف.")

    except Exception as e:
        st.error(f"خطأ تقني: {e}")

# العرض والبحث
if not st.session_state.full_database.empty:
    st.divider()
    search = st.text_input("🔍 ابحث عن أي مورد أو تفاصيل تواصل:")
    
    display_df = st.session_state.full_database
    if search:
        mask = display_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        display_df = display_df[mask]
    
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    
    # تصدير إكسيل
    out_buf = io.BytesIO()
    with pd.ExcelWriter(out_buf, engine='openpyxl') as writer:
        display_df.to_excel(writer, index=False, sheet_name='Suppliers')
    
    st.download_button("📥 تحميل قاعدة البيانات المحدثة (Excel)", 
                       data=out_buf.getvalue(), 
                       file_name="Organized_Suppliers.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
else:
    st.info("يرجى رفع الملف واختيار الأقسام للبدء.")
