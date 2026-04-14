import streamlit as st
import pandas as pd
import io
import re
import json
import os

# =============================
# CONFIG
# =============================
st.set_page_config(page_title="Supplier Manager Pro", layout="wide")
DATA_FILE = "suppliers_data.json"

# =============================
# UTILS
# =============================
def normalize_name(name):
    name = str(name).lower()
    name = re.sub(r'\s+', ' ', name)
    name = re.sub(r'[^a-z0-9 ]', '', name)
    return name.strip()


def merge_categories(old, new):
    old_list = [c.strip() for c in old.split('/') if c.strip()]
    if new not in old_list:
        old_list.append(new)
    return " / ".join(old_list)


def auto_category(name):
    name = name.lower()
    if "electric" in name:
        return "Électricité"
    elif "plomb" in name:
        return "Plomberie"
    elif "mecan" in name:
        return "Mécanique"
    return None

# =============================
# STORAGE
# =============================
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# =============================
# INIT
# =============================
if "data_dict" not in st.session_state:
    st.session_state.data_dict = load_data()

# =============================
# UI
# =============================
st.title("🏢 Supplier Manager Pro")

AVAILABLE_CATEGORIES = [
    "Mécanique", "Électricité", "Plomberie", "PPE", 
    "Consommables", "Pièces", "Outillage", 
    "Maintenance", "IT", "Chimique", "BTP"
]

# =============================
# IMPORT EXCEL
# =============================
uploaded_file = st.file_uploader("📥 Import Excel", type=["xlsx"])

if uploaded_file:
    xl = pd.ExcelFile(uploaded_file)
    sheets = st.multiselect("Choisir les feuilles", xl.sheet_names, default=xl.sheet_names)

    if st.button("🚀 Importer"):
        added, updated = 0, 0

        for s in sheets:
            df = pd.read_excel(uploaded_file, sheet_name=s)

            for _, row in df.iterrows():
