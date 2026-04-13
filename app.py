import streamlit as st
import pandas as pd
import io

# 1. الإعدادات العامة للصفحة
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# تصميم الواجهة
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 3px solid #10B981; padding-bottom: 10px; }
    </style>
    """, unsafe_allow_html=True)

# 2. وظيفة المعالجة الفائقة - تحول البيانات إلى قائمة قواميس بسيطة لتفادي مشاكل الفهرس
def get_clean_records(df_raw, category_name):
    """تحليل الورقة وتحويلها إلى قائمة من السجلات البسيطة"""
    if df_raw.empty:
        return []

    # تحويل كل شيء لنصوص وحذف NaN
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # البحث عن سطر العنوان
    header_idx = -1
    col_map = {}
    for i in range(min(50, len(df))):
        row = [str(x).lower() for x in df.iloc[i].values]
        matches = 0
        current_map = {}
        for target, keys in mapping.items():
            for idx, cell_val in enumerate(row):
                if any(k in cell_val for k in keys):
                    current_map[idx] = target
                    matches += 1
                    break
        if matches >= 1:
            header_idx = i
            col_map = current_map
            break

    records = []
    if header_idx != -1:
        # استخراج البيانات بناءً على الأعمدة المكتشفة
        data_rows = df.iloc[header_idx + 1:]
        for _, row in data_rows.iterrows():
            record = {'Catégorie': category_name}
            # تعبئة الحقول الأساسية
            for target in mapping.keys():
                record[target] = ""
            
            # تعبئة البيانات المكتشفة
            for col_idx, target_name in col_map.items():
                record[target_name] = str(row.iloc[col_idx]).strip()
            
            # إضافة السجل فقط إذا كان اسم المورد موجوداً
            if record.get('Nom du Fournisseur') and record['Nom du Fournisseur'].lower() not in ['nom', 'designation', 'fournisseur', 'اسم']:
                records.append(record)
    else:
        # حل بديل إذا لم يتم العثور على عناوين: نعتبر أول عمود غير فارغ هو الاسم
        for _, row in df.iterrows():
            val = str(row.iloc[0]).strip()
            if val and val.lower() not in ['nan', '']:
                records.append({
                    'Nom du Fournisseur': val,
                    'Catégorie': category_name,
                    'Adresse': "", 'Téléphone': "", 'Mobile': "", 'E-mail': ""
                })
                
    return records

# 3. إدارة الحالة (Session State)
if 'data_list' not in st.session_state:
    st.session_state.data_list = []

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs (Version Stable)</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Ajout Manuel"])

with tab1:
    uploaded_file = st.file_uploader("Charger un fichier Excel (.xlsx)", type=['xlsx'])
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheets = st.multiselect("Sélectionnez les feuilles :", xl.sheet_names, default=xl.sheet_names)
            
            if st.button("🚀 Importer et Fusionner"):
                new_records_count = 0
                for s in sheets:
                    # قراءة بدون هيدر لتجنب مشاكل التكرار في pandas
                    df_raw = pd.read_excel(uploaded_file, sheet_name=s, header=None)
                    records = get_clean_records(df_raw, s)
                    
                    # إضافة السجلات الجديدة للقائمة مع تجنب التكرار بالاسم
                    existing_names = [r['Nom du Fournisseur'].lower() for r in st.session_state.data_list]
                    for rec in records:
                        if rec['Nom du Fournisseur'].lower() not in existing_names:
                            st.session_state.data_list.append(rec)
                            new_records_count += 1
                
                st.success(f"✅ Opération réussie : {new_records_count} nouveaux fournisseurs ajoutés.")
        except Exception as e:
            st.error(f"❌ Erreur lors de l'import : {str(e)}")

with tab2:
    with st.form("manual_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom de l'établissement *")
            cat = st.text_input("Catégorie")
            tel = st.text_input("Téléphone")
        with c2:
            mob = st.text_input("Mobile")
            mail = st.text_input("E-mail")
            adr = st.text_area("Adresse")
        
        if st.form_submit_button("💾 Enregistrer"):
            if name:
                existing_names = [r['Nom du Fournisseur'].lower() for r in st.session_state.data_list]
                if name.lower() not in existing_names:
                    st.session_state.data_list.append({
                        "Nom du Fournisseur": name, "Catégorie": cat, "Téléphone": tel, 
                        "Mobile": mob, "Adresse": adr, "E-mail": mail
                    })
                    st.success(f"✔️ '{name}' ajouté.")
                else:
                    st.warning("Ce fournisseur existe déjà.")
            else:
                st.error("Le nom est obligatoire.")

# 4. عرض النتائج النهائية
st.divider()
if st.session_state.data_list:
    # تحويل القائمة البسيطة إلى DataFrame فقط عند العرض
    full_df = pd.DataFrame(st.session_state.data_list)
    
    st.subheader(f"📋 Liste Unifiée ({len(full_df)} fournisseurs)")
    
    search = st.text_input("🔍 Rechercher...")
    if search:
        full_df = full_df[full_df.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)]

    st.dataframe(full_df, use_container_width=True, hide_index=True)
    
    col_x1, col_x2 = st.columns([1, 4])
    with col_x1:
        # تصدير البيانات
        output = io.BytesIO()
        full_df.to_excel(output, index=False, engine='openpyxl')
        st.download_button("📥 Télécharger Excel", output.getvalue(), "base_fournisseurs.xlsx")
    with col_x2:
        if st.button("🗑️ Vider la base"):
            st.session_state.data_list = []
            st.rerun()
else:
    st.info("Aucune donnée disponible.")
