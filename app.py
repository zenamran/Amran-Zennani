import streamlit as st
import pandas as pd

# إعداد الصفحة
st.set_page_config(page_title="منظم الموردين الذكي", layout="wide")

st.title("🛡️ نظام إدارة الموردين (ترتيب آلي + تحويل ذكي)")

# وظيفة الترتيب الذكي (AI Logic)
def smart_clean(df):
    # مصفوفة لتحويل الأسماء العشوائية إلى أسماء قياسية
    mapping = {
        'الشركة': 'اسم المورد', 'المورد': 'اسم المورد', 'Supplier': 'اسم المورد', 'Name': 'اسم المورد',
        'الهاتف': 'رقم التواصل', 'Phone': 'رقم التواصل', 'Mobile': 'رقم التواصل', 'Tel': 'رقم التواصل',
        'النشاط': 'الفئة', 'Category': 'الفئة', 'Type': 'الفئة', 'الخدمة': 'الفئة'
    }
    # إعادة تسمية الأعمدة إذا وجدت في القاموس
    df = df.rename(columns=mapping)
    # تنظيف البيانات من الفراغات (استخدام map بدلاً من applymap للإصدارات الجديدة)
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    # إزالة الصفوف الفارغة تماماً
    df = df.dropna(how='all')
    return df

# واجهة رفع الملفات
st.markdown("### 📥 ارفع ملف الإكسيل غير المرتب")
uploaded_file = st.file_uploader("اختر ملف (xlsx أو csv)", type=['xlsx', 'csv'])

if uploaded_file:
    try:
        # قراءة الملف
        if uploaded_file.name.endswith('xlsx'):
            new_df = pd.read_excel(uploaded_file)
        else:
            new_df = pd.read_csv(uploaded_file)
        
        st.info("💡 تم اكتشاف الملف بنجاح. اضغط على الزر أدناه لتنظيمه.")

        if st.button("🪄 ترتيب البيانات الآن"):
            cleaned_df = smart_clean(new_df)
            
            st.success("✅ تم الترتيب بنجاح! إليك البيانات المنظمة:")
            
            # عرض البيانات
            st.dataframe(cleaned_df, use_container_width=True)
            
            # ميزة التحميل الفوري للملف النظيف
            csv = cleaned_df.to_csv(index=False).encode('utf-8-sig')
            st.download_button(
                label="📥 تحميل القائمة المرتبة (Excel/CSV)",
                data=csv,
                file_name=f"Cleaned_{uploaded_file.name.split('.')[0]}.csv",
                mime='text/csv',
            )
            
            st.balloons() # احتفالاً بالنجاح!

    except Exception as e:
        st.error(f"حدث خطأ أثناء المعالجة: {e}")

else:
    st.info("بانتظار رفع الملف للبدء في عملية التنظيم.")

# تعليمات للمستخدم
with st.expander("❓ كيف يعمل الترتيب الذكي؟"):
    st.write("""
    1. التطبيق يبحث عن الكلمات المفتاحية في رؤوس الأعمدة (مثل: هاتف، شركة، مورد).
    2. يقوم بتوحيدها لتصبح قاعدة بيانات احترافية.
    3. يحذف الفراغات والأخطاء الناتجة عن الإدخال اليدوي.
    """)
