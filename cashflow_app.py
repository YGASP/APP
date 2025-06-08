import streamlit as st
import pandas as pd
import datetime
import gspread
import os
import json
import plotly.express as px
from oauth2client.service_account import ServiceAccountCredentials

# הגדרות עמוד
st.set_page_config(page_title="ניהול תזרים", layout="wide")

# הגדרת הרשאות - תומך גם בהרצה מקומית וגם בענן
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]

if "GOOGLE_CREDENTIALS" in st.secrets:
    creds_dict = json.loads(st.secrets["GOOGLE_CREDENTIALS"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
else:
    CREDENTIALS_PATH = "credentials.json"
    if not os.path.exists(CREDENTIALS_PATH):
        st.error("⚠️ הקובץ credentials.json לא נמצא בתיקייה. העלה אותו או הגדר Secret.")
        st.stop()
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)

# חיבור ל־Google Sheets
client = gspread.authorize(creds)
sheet_id = "14P_Qe5E_DZmuqYSns6_Z2y4aSZ9-kH2r67FzYLAbXGw"
transactions_ws = client.open_by_key(sheet_id).worksheet("transactions")

# טעינת נתונים

def load_data(ws, columns):
    data = ws.get_all_records()
    df = pd.DataFrame(data)
    for col in columns:
        if col not in df.columns:
            df[col] = None
    return df[columns]

transactions_cols = ['תאריך', 'סוג', 'סכום', 'מטבע', 'מקור', 'קטגוריה', 'תיאור', 'סטטוס']
transactions = load_data(transactions_ws, transactions_cols)

# שמירת נתונים

def save_data(ws, df):
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())

# 🧠 היסטוריית התממשות
@st.cache_data(show_spinner=False)
def get_realization_rate(df):
    df = df.copy()
    df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')
    df['SKU'] = df['קטגוריה'].str.extract(r"מכירות (.+)")
    forecast_df = df[df['סטטוס'] == 'תחזית']
    confirmed_df = df[df['סטטוס'] == 'אושר']

    realization = confirmed_df.groupby('SKU')['סכום'].sum() / forecast_df.groupby('SKU')['סכום'].sum()
    return realization.fillna(1.0).to_dict()

realization_map = get_realization_rate(transactions)

# תפריט ניווט
st.sidebar.title("תפריט")
page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות", "תחזיות"])

# 📦 תחזית מכירות
st.sidebar.markdown("---")
st.sidebar.subheader("📦 תחזית מכירות")
with st.sidebar.expander("הזנת תחזית לפי כמות ורווח ליחידה", expanded=False):
    st.markdown("**💰 רווח ליחידה לפי SKU:**")
    puncho_blue_profit = st.number_input("Puncho כחול (USD)", min_value=0.0, format="%.2f", key="blue_profit")
    puncho_red_profit = st.number_input("Puncho אדום (USD)", min_value=0.0, format="%.2f", key="red_profit")

    sku_profit_map = {
        "Puncho כחול": puncho_blue_profit,
        "Puncho אדום": puncho_red_profit
    }

    with st.form("sales_forecast_form"):
        col1, col2 = st.columns(2)
        with col1:
            sku = st.selectbox("בחר מוצר", list(sku_profit_map.keys()))
        with col2:
            units = st.number_input("צפי יחידות לחודש", min_value=1, step=1)

        forecast_month = st.date_input("בחר חודש (ייקבע ל־1 לחודש)", datetime.date.today().replace(day=1))
        forecast_submit = st.form_submit_button("📤 הוסף תחזית")

        if forecast_submit:
            profit_per_unit = sku_profit_map.get(sku, 0)
            realization_rate = realization_map.get(sku, 0.85)
            total_forecast = round(units * profit_per_unit * realization_rate, 2)

            new_row = {
                'תאריך': forecast_month.strftime('%Y-%m-01'),
                'סוג': 'הכנסה',
                'סכום': total_forecast,
                'מטבע': '$',
                'מקור': 'פיוניר',
                'קטגוריה': f"מכירות {sku}",
                'תיאור': f"{units} יחידות × ${profit_per_unit:.2f} × {realization_rate:.2f}",
                'סטטוס': 'תחזית'
            }

            new_df = pd.DataFrame([new_row])
            transactions = pd.concat([transactions, new_df], ignore_index=True)
            save_data(transactions_ws, transactions)
            st.success(f"✅ תחזית נרשמה לפי שיעור מימוש {realization_rate:.2f}: ${total_forecast:.2f}")
