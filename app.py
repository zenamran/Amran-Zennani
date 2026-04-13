import streamlit as st
import pandas as pd
import io

# 1. إعدادات الصفحة الأساسية
st.set_page_config(
    page_title="Système Pro - Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# تصميم واجهة المستخدم بلمسة احترافية
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    .main-header { color: #2E7D32; font-weight: bold; border-bottom: 2px solid #2E7D32; padding-bottom: 10px; margin-bottom: 20px; }
    .status-box { padding: 10px; border-radius: 5px; margin-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. إدارة البيانات في الذاكرة (مع توفير خيار الحفظ المحلي)
if 'suppliers_db' not in st.session_state:
    st.session_state.suppliers_db = []

# وظيفة لتنظيف البيانات وحل مشكلة (float found) التي ظهرت في الصور
def safe_str(val):
    """تحويل أي قيمة إلى نص بشكل آمن وتجنب أخطاء القيم الفارغة"""
    if pd.isna(val) or val is None:
        return ""
    return str(val).strip()

def process_excel_sheet(df_raw, sheet_name):
    """معالجة ورقة الإكسيل بمرونة عالية"""
    if df_raw.empty:
        return []
    
    # تحويل كافة البيانات لنصوص فوراً لتجنب خطأ sequence item 0: expected str instance
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    
    # البحث عن الأعمدة
    mapping = {
        'Nom': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Tel': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax', 'mobile', 'mob', 'محمول']
    }
    
    header_row = -1
    col_map = {}
    
    # فحص أول 20 سطر للبحث عن العناوين
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

# 3. واجهة التطبيق
st.markdown("<h1 class='main-header'>🏢 مدير قاعدة بيانات الموردين الذكي</h1>", unsafe_allow_html=True)

menu = ["📂 استيراد ودمج البيانات", "➕ إضافة مورد يدوياً", "📋 عرض وتحميل القاعدة"]
choice = st.sidebar.selectbox("القائمة الرئيسية", menu)

if choice == "📂 استيراد ودمج البيانات":
    st.subheader("تحميل ملفات Excel")
    file = st.file_uploader("اختر ملف .xlsx", type="xlsx")
    
    if file:
        xl = pd.ExcelFile(file)
        all_sheets = xl.sheet_names
        selected_sheets = st.multiselect("اختر أوراق العمل المراد دمجها:", all_sheets, default=all_sheets)
        
        if st.button("🚀 بدء عملية المعالجة والدمج"):
            progress_bar = st.progress(0)
            new_records = 0
            
            for i, sheet in enumerate(selected_sheets):
                try:
                    df_sheet = pd.read_excel(file, sheet_name=sheet, header=None)
                    results = process_excel_sheet(df_sheet, sheet)
                    
                    for item in results:
                        # البحث عن المورد الحالي لدمج الفئات
                        existing = next((x for x in st.session_state.suppliers_db if x['Nom'].lower() == item['Nom'].lower()), None)
                        
                        if existing:
                            # إذا وجد المورد، ندمج الفئة بفاصل /
                            if item['Catégories'] not in existing['Catégories']:
                                existing['Catégories'] += f" / {item['Catégories']}"
                        else:
                            st.session_state.suppliers_db.append(item)
                            new_records += 1
                except Exception as e:
                    st.error(f"خطأ في ورقة {sheet}: {str(e)}")
                
                progress_bar.progress((i + 1) / len(selected_sheets))
            
            st.success(f"✅ تمت العملية بنجاح! تم إضافة {new_records} مورد جديد وتحديث التخصصات للبقية.")

elif choice == "➕ إضافة مورد يدوياً":
    st.subheader("إدخال مورد جديد")
    with st.form("manual_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("اسم الشركة/المورد *")
            cats = st.text_input("التخصصات (مثال: ميكانيك / أدوات)")
        with col2:
            contact = st.text_input("رقم الهاتف / البريد")
            address = st.text_area("العنوان الكامل")
            
        if st.form_submit_button("حفظ المورد"):
            if name:
                existing = next((x for x in st.session_state.suppliers_db if x['Nom'].lower() == name.lower()), None)
                if existing:
                    existing['Catégories'] += f" / {cats}"
                    st.info("المورد موجود مسبقاً، تم تحديث فئاته.")
                else:
                    st.session_state.suppliers_db.append({"Nom": name, "Catégories": cats, "Contact": contact, "Adresse": address})
                    st.success("تم الحفظ بنجاح.")
            else:
                st.error("الاسم مطلوب!")

elif choice == "📋 عرض وتحميل القاعدة":
    st.subheader("قاعدة البيانات الموحدة")
    
    if st.session_state.suppliers_db:
        df_display = pd.DataFrame(st.session_state.suppliers_db)
        
        # محرك بحث داخلي
        search = st.text_input("🔍 بحث سريع عن مورد أو فئة:")
        if search:
            df_display = df_display[df_display.apply(lambda r: search.lower() in str(r).lower(), axis=1)]
            
        st.dataframe(df_display, use_container_width=True)
        
        # تصدير البيانات
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
            df_display.to_excel(writer, index=False, sheet_name='Fournisseurs')
        
        st.download_button(
            label="📥 تحميل القاعدة كاملة (Excel)",
            data=buffer.getvalue(),
            file_name="Base_Fournisseurs_Optimisee.xlsx",
            mime="application/vnd.ms-excel"
        )
        
        if st.button("🗑️ مسح كافة البيانات"):
            st.session_state.suppliers_db = []
            st.rerun()
    else:
        st.info("قاعدة البيانات فارغة حالياً. قم باستيراد ملف إكسيل للبدء.")
