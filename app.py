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

# قائمة الفئات الافتراضية
AVAILABLE_CATEGORIES = [
    "Mécanique", "Électricité", "Plomberie", "PPE / Protection", 
    "Consommables", "Pièces de rechange", "Outillage", 
    "Maintenance", "Informatique", "Produits Chimiques", "BTP"
]

# 2. وظيفة المعالجة - تحويل البيانات لسجلات ذكية تدمج الفئات
def get_clean_records(df_raw, category_name):
    if df_raw.empty: return []
    
    df = df_raw.astype(str).replace(['nan', 'None', 'NaN', 'null'], '')
    
    mapping = {
        'Nom du Fournisseur': ['nom', 'fournisseur', 'designation', 'désignation', 'société', 'company', 'اسم', 'المورد', 'établissement'],
        'Adresse': ['adresse', 'address', 'lieu', 'wilaya', 'عنوان', 'مقر', 'localisation', 'ville'],
        'Téléphone': ['tél', 'tel', 'phone', 'fixe', 'هاتف', 'الفاكس', 'fax'],
        'Mobile': ['mobile', 'mob', 'محمول', 'جوال', 'رقم'],
        'E-mail': ['email', 'e-mail', 'mail', 'البريد', 'إيميل'],
        'FAX': ['FAX', 'Fax', 'fax','الفاكس' ,'فاكس']
    }

    header_idx = -1
    col_map = {}
    for i in range(min(50, len(df))):
        row = [str(x).lower() for x in df.iloc[i].values]
        current_map = {}
        matches = 0
        for target, keys in mapping.items():
            for idx, cell in enumerate(row):
                if any(k in cell for k in keys):
                    current_map[idx] = target
                    matches += 1
                    break
        if matches >= 1:
            header_idx, col_map = i, current_map
            break

    records = []
    if header_idx != -1:
        data_rows = df.iloc[header_idx + 1:]
        for _, row in data_rows.iterrows():
            record = {'Catégories': category_name}
            for target in mapping.keys(): record[target] = ""
            for col_idx, target_name in col_map.items():
                record[target_name] = str(row.iloc[col_idx]).strip()
            
            if record.get('Nom du Fournisseur') and record['Nom du Fournisseur'].lower() not in ['nom', 'designation', 'fournisseur', 'اسم']:
                records.append(record)
    return records

# 3. إدارة الحالة (Session State)
if 'data_list' not in st.session_state:
    st.session_state.data_list = []

st.markdown("<h1 class='main-header'>🏢 Gestionnaire des Fournisseurs (Multi-Catégories)</h1>", unsafe_allow_html=True)

tab1, tab2 = st.tabs(["📥 Importation Excel", "➕ Ajout Manuel"])

with tab1:
    uploaded_file = st.file_uploader("Charger un fichier Excel", type=['xlsx'])
    if uploaded_file:
        try:
            xl = pd.ExcelFile(uploaded_file)
            sheets = st.multiselect("Sélectionnez les feuilles (Les noms des feuilles seront les catégories) :", xl.sheet_names, default=xl.sheet_names)
            
            if st.button("🚀 Fusionner les données"):
                new_added = 0
                updated_cats = 0
                for s in sheets:
                    df_raw = pd.read_excel(uploaded_file, sheet_name=s, header=None)
                    records = get_clean_records(df_raw, s)
                    
                    for rec in records:
                        name_lower = rec['Nom du Fournisseur'].lower().strip()
                        # البحث عن المورد الحالي في القائمة
                        existing_idx = next((i for i, item in enumerate(st.session_state.data_list) if item['Nom du Fournisseur'].lower().strip() == name_lower), None)
                        
                        if existing_idx is None:
                            # مورد جديد تماماً
                            st.session_state.data_list.append(rec)
                            new_added += 1
                        else:
                            # المورد موجود، نقوم بدمج الفئة الجديدة مع الفئات السابقة
                            current_cats = str(st.session_state.data_list[existing_idx]['Catégories'])
                            if s.strip() not in [c.strip() for c in current_cats.split('/')]:
                                st.session_state.data_list[existing_idx]['Catégories'] = f"{current_cats} / {s}"
                                updated_cats += 1
                
                st.success(f"✅ Terminé : {new_added} nouveaux fournisseurs et {updated_cats} mises à jour de catégories.")
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

with tab2:
    with st.form("manual_entry", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            name = st.text_input("Nom de l'établissement *")
            selected_cats = st.multiselect("Sélectionner des catégories", AVAILABLE_CATEGORIES)
            custom_cat = st.text_input("Ou saisir une catégorie personnalisée (كتابة فئة أخرى)")
            tel = st.text_input("Téléphone")
        with c2:
            mob = st.text_input("Mobile")
            mail = st.text_input("E-mail")
            adr = st.text_area("Adresse")
        
        if st.form_submit_button("💾 Enregistrer"):
            if name:
                # دمج الفئات المختارة مع الفئة المكتوبة يدوياً
                all_cats = list(selected_cats)
                if custom_cat.strip():
                    all_cats.append(custom_cat.strip())
                
                cat_string = " / ".join(all_cats) if all_cats else "Général"
                name_lower = name.lower().strip()
                existing_idx = next((i for i, item in enumerate(st.session_state.data_list) if item['Nom du Fournisseur'].lower().strip() == name_lower), None)
                
                if existing_idx is None:
                    st.session_state.data_list.append({
                        "Nom du Fournisseur": name, "Catégories": cat_string, 
                        "Téléphone": tel, "Mobile": mob, "Adresse": adr, "E-mail": mail
                    })
                    st.success("Mورد جديد أضيف بنجاح")
                else:
                    # دمج الفئات يدوياً إذا أضيف نفس المورد
                    current = str(st.session_state.data_list[existing_idx]['Catégories'])
                    current_list = [c.strip() for c in current.split('/')]
                    
                    for c in all_cats:
                        if c not in current_list:
                            current = f"{current} / {c}"
                    
                    st.session_state.data_list[existing_idx]['Catégories'] = current
                    st.info("تم تحديث فئات المورد الموجود مسبقاً")
            st.rerun()

# 4. عرض النتائج
st.divider()
if st.session_state.data_list:
    df_final = pd.DataFrame(st.session_state.data_list)
    st.subheader(f"📋 Liste Unifiée ({len(df_final)} fournisseurs)")
    
    search = st.text_input("🔍 Rechercher un fournisseur ou une catégorie :")
    if search:
        mask = df_final.astype(str).apply(lambda x: x.str.contains(search, case=False, na=False)).any(axis=1)
        df_final = df_final[mask]

    st.dataframe(df_final, use_container_width=True, hide_index=True)
    
    col1, col2 = st.columns([1, 4])
    with col1:
        out = io.BytesIO()
        df_final.to_excel(out, index=False, engine='openpyxl')
        st.download_button("📥 Exporter Excel", out.getvalue(), "base_fournisseurs.xlsx")
    with col2:
        if st.button("🗑️ Vider la base"):
            st.session_state.data_list = []
            st.rerun()
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
