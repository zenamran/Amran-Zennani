import streamlit as st
import pandas as pd
import io

# 1. الإعدادات العامة للصفحة
st.set_page_config(
    page_title="Système de Gestion des Fournisseurs",
    page_icon="🏢",
    layout="wide"
)

# تصميم الواجهة باستخدام CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Segoe+UI:wght@400;600&display=swap');
    html, body, [class*="css"] { font-family: 'Segoe UI', sans-serif; }
    .main-header { color: #1E293B; font-weight: 700; border-bottom: 3px solid #10B981; padding-bottom: 10px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    </style>
    """, unsafe_allow_html=True)

# 2. دالة التنظيف "القصوى" - تحل مشكلة Reindexing نهائياً
def process_excel_sheet(df):
    """تحويل ورقة الإكسيل إلى بيانات نظيفة بأسماء أعمدة فريدة ومضمونة"""
    if df.empty:
        return pd.DataFrame()

    # الخطوة 1: تحويل كل شيء إلى نصوص فوراً لقطع الطريق على أخطاء الـ float
    df = df.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')

    # الخطوة 2: إعادة ضبط الفهرس والأعمدة تماماً لتجنب مشكلة Reindexing
    # نقوم بتسمية الأعمدة بأرقام مؤقتة لضمان التفرد التام
    df.columns = [f"temp_col_{i}" for i in range(len(df.columns))]
    df = df.reset_index(drop=True)

    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل']
    }

    # الخطوة 3: البحث عن سطر العناوين الحقيقي (المسح حتى أول 50 سطر)
    found_header_idx = -1
    max_matches = 0
    for i in range(min(50, len(df))):
        row_content = " ".join(df.iloc[i].values).lower()
        matches = sum(1 for keys in mapping.values() if any(k in row_content for k in keys))
        if matches > max_matches:
            max_matches = matches
            found_header_idx = i

    # إذا وجدنا سطر عناوين محتمل
    if found_header_idx != -1 and max_matches >= 1:
        # استخراج العناوين الجديدة
        new_raw_cols = [str(val).strip() for val in df.iloc[found_header_idx]]
        # بناء قاموس لإعادة التسمية
        final_columns_map = {}
        for idx, col_name in enumerate(new_raw_cols):
            c_low = col_name.lower()
            for target, keywords in mapping.items():
                if target not in final_columns_map.values() and any(k in c_low for k in keywords):
                    final_columns_map[f"temp_col_{idx}"] = target
                    break
        
        # قص الجدول من بعد سطر العناوين
        df = df.iloc[found_header_idx + 1:].copy()
        df = df.rename(columns=final_columns_map)
    else:
        # حل بديل: إذا لم نجد عناوين واضحة، نعتبر العمود الأول هو الاسم
        df = df.rename(columns={"temp_col_0": "Nom du Fournisseur"})

    # الخطوة 4: الاحتفاظ بالأعمدة المطلوبة فقط وبناء هيكل جديد تماماً
    target_cols = ['Nom du Fournisseur', 'Adresse', 'Téléphone', 'Mobile', 'E-mail']
    available_cols = [c for c in target_cols if c in df.columns]
    
    if available_cols:
        # إنشاء نسخة جديدة تماماً لضمان عدم وجود مراجع للفهرس القديم المكرر
        df_final = df[available_cols].copy()
    else:
        return pd.DataFrame()

    # تنظيف القيم الفارغة والأسطر التي تكرر العناوين
    if 'Nom du Fournisseur' in df_final.columns:
        df_final = df_final[df_final['Nom du Fournisseur'].str.strip() != ""]
        header_vals = ['nom', 'designation', 'fournisseur', 'اسم', 'المورد', 'établissement']
        df_final = df_final[~df_final['Nom du Fournisseur'].str.lower().isin(header_vals)]

    return df_final.reset_index(drop=True)

# 3. إدارة حالة التطبيق (Session State)
if 'master_db' not in st.session_state:
    st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Saisie Manuelle"])

with tab1:
    st.subheader("Importer un fichier Excel")
    uploaded_file = st.file_uploader("Fichier .xlsx", type=['xlsx'])
    
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheets = st.multiselect("Sélectionnez les feuilles :", xl.sheet_names, default=xl.sheet_names)
            
            if st.button("🚀 Fusionner et Nettoyer"):
                all_processed_data = []
                for s in sheets:
                    # قراءة البيانات الخام بدون اعتبار أي سطر كعنوان في البداية لتجنب تكرار الأسماء
                    raw_data = pd.read_excel(uploaded_file, sheet_name=s, header=None)
                    clean_data = process_excel_sheet(raw_data)
                    if not clean_data.empty:
                        clean_data['Catégorie'] = s
                        all_processed_data.append(clean_data)
                
                if all_processed_data:
                    # دمج كل البيانات المعالجة في جدول واحد جديد
                    new_batch = pd.concat(all_processed_data, axis=0, ignore_index=True).reset_index(drop=True)
                    
                    # الدمج مع قاعدة البيانات الكلية
                    full_db = pd.concat([st.session_state.master_db, new_batch], axis=0, ignore_index=True)
                    
                    # حذف التكرارات بناءً على اسم المورد فقط
                    if 'Nom du Fournisseur' in full_db.columns:
                        st.session_state.master_db = full_db.drop_duplicates(subset=['Nom du Fournisseur'], keep='first').reset_index(drop=True)
                        st.success(f"✅ Opération réussie : {len(new_batch)} fournisseurs importés.")
                else:
                    st.warning("⚠️ Aucune donnée n'a été trouvée dans les feuilles sélectionnées.")
        except Exception as e:
            st.error(f"❌ Erreur critique : {str(e)}")

with tab2:
    st.subheader("Ajout manuel")
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
                new_entry = pd.DataFrame([{"Nom du Fournisseur": name, "Catégorie": cat, "Téléphone": tel, "Mobile": mob, "Adresse": adr, "E-mail": mail}])
                st.session_state.master_db = pd.concat([st.session_state.master_db, new_entry], ignore_index=True).drop_duplicates(subset=['Nom du Fournisseur']).reset_index(drop=True)
                st.success(f"Fournisseur '{name}' ajouté.")
            else:
                st.error("Le nom est obligatoire.")

# 4. عرض النتائج والتحميل
st.divider()
if not st.session_state.master_db.empty:
    db_to_show = st.session_state.master_db
    st.subheader(f"📋 Liste Unifiée ({len(db_to_show)} fournisseurs)")
    
    search_term = st.text_input("🔍 Recherche rapide :")
    if search_term:
        mask = db_to_show.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        db_to_show = db_to_show[mask]

    st.dataframe(db_to_show, use_container_width=True, hide_index=True)
    
    col_btn1, col_btn2 = st.columns([1, 4])
    with col_btn1:
        # تصدير البيانات
        output = io.BytesIO()
        db_to_show.to_excel(output, index=False, engine='openpyxl')
        st.download_button("📥 Télécharger en Excel", output.getvalue(), "fournisseurs_base_finale.xlsx")
    with col_btn2:
        if st.button("🗑️ Vider la base de données"):
            st.session_state.master_db = pd.DataFrame(columns=['Nom du Fournisseur', 'Catégorie', 'Téléphone', 'Mobile', 'Adresse', 'E-mail'])
            st.rerun()
else:
    st.info("Aucune donnée disponible. Veuillez importer un fichier ou ajouter un fournisseur.")
