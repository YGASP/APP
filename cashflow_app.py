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

transactions_cols = ['תאריך', 'סוג', 'סכום', 'מטבע', 'מקור', 'קטגוריה', 'תיאור']
transactions = load_data(transactions_ws, transactions_cols)

# שמירת נתונים
def save_data(ws, df):
    ws.clear()
    ws.update([df.columns.values.tolist()] + df.values.tolist())

# תפריט ניווט
st.sidebar.title("תפריט")
page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות"])
if st.sidebar.button("➕ הוספה מהירה"):
    page = "הוספה"
st.sidebar.markdown("---")
st.sidebar.markdown("📄 [קובץ עזרה](https://example.com/help)")

# עיצוב כספים
def format_money(val, currency):
    try:
        val = float(val)
        return "{:,.2f} {}".format(val, currency)
    except:
        return f"{val} {currency}"

# ==========================================
# עמוד חזית
# ==========================================
if page == "חזית":
    st.title("🌟 ניהול תזרים")

    df = transactions.copy()
    df['סכום'] = pd.to_numeric(df['סכום'], errors='coerce').fillna(0)
    df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')
    df['חודש'] = df['תאריך'].dt.to_period('M').astype(str)

    col1, col2, col3 = st.columns(3)
    with col1:
        p_in = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הכנסה')]['סכום'].sum()
        p_out = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הוצאה')]['סכום'].sum()
        st.metric("פיוניר", format_money(p_in - p_out, '$'))
    with col2:
        b_in = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הכנסה')]['סכום'].sum()
        b_out = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הוצאה')]['סכום'].sum()
        st.metric("ישראלי", format_money(b_in - b_out, '₪'))
    with col3:
        total = (p_in - p_out) * 3.8 + (b_in - b_out)
        st.metric("מאזן כולל (₪)", format_money(total, '₪'))

    st.subheader("גרף חודשי - הכנסות/הוצאות")
    chart_data = df.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    fig = px.bar(chart_data, x='חודש', y='סכום', color='סוג', barmode='group', title="תזרים לפי חודשים")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧁 פיזור לפי קטגוריה")
    pie_data = df.groupby(['קטגוריה'])['סכום'].sum().reset_index()
    pie_data = pie_data[pie_data['סכום'] > 0]
    if not pie_data.empty:
        fig2 = px.pie(pie_data, names='קטגוריה', values='סכום', title="פיזור לפי קטגוריה")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 השוואה חודשית - הכנסה מול הוצאה")
    month_compare_raw = df.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    month_compare = month_compare_raw.pivot(index='חודש', columns='סוג', values='סכום').fillna(0).reset_index()
    if 'הכנסה' not in month_compare.columns:
        month_compare['הכנסה'] = 0
    if 'הוצאה' not in month_compare.columns:
        month_compare['הוצאה'] = 0
    fig3 = px.line(month_compare, x='חודש', y=['הכנסה', 'הוצאה'], markers=True, title="השוואה חודשית")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🔥 Top 5 קטגוריות הוצאה")
    top_expense = df[df['סוג'] == 'הוצאה'].groupby('קטגוריה')['סכום'].sum().nlargest(5).reset_index()
    st.dataframe(top_expense, use_container_width=True)

# ==========================================
# עמוד הוספה
# ==========================================
elif page == "הוספה":
    st.title("🗓 הוספת הכנסה / הוצאה")

    with st.form("form_transaction"):
        col1, col2, col3 = st.columns(3)
        with col1:
            date = st.date_input("תאריך", datetime.date.today())
            amount = st.number_input("סכום", min_value=0.0, format="%.2f")
            currency = st.selectbox("מטבע", ['₪', '$'])
        with col2:
            kind = st.selectbox("סוג", ['הכנסה', 'הוצאה'])
            source = st.selectbox("מקור", ['פיוניר', 'ישראלי'])
            category = st.text_input("קטגוריה")
        with col3:
            description = st.text_input("תיאור נוסף")

        submitted = st.form_submit_button("הוספה")

        if submitted:
            new_row = pd.DataFrame.from_records([{
                'תאריך': date.strftime('%Y-%m-%d'),
                'סוג': kind,
                'סכום': amount,
                'מטבע': currency,
                'מקור': source,
                'קטגוריה': category,
                'תיאור': description
            }])
            transactions = pd.concat([transactions, new_row], ignore_index=True)
            save_data(transactions_ws, transactions)
            st.success("✅ נשמר בהצלחה ל־Google Sheets!")

# ==========================================
# עמוד רשומות
# ==========================================
elif page == "רשומות":
    st.title("📋 כל הרשומות")
    df = transactions.copy()
    df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')

    with st.expander("🔍 סינון מתקדם"):
        col1, col2, col3 = st.columns(3)
        with col1:
            date_range = st.date_input("טווח תאריכים", [])
        with col2:
            source_filter = st.multiselect("מקור", options=df['מקור'].unique())
        with col3:
            category_filter = st.multiselect("קטגוריה", options=df['קטגוריה'].unique())

    if date_range:
        if len(date_range) == 2:
            df = df[(df['תאריך'] >= pd.to_datetime(date_range[0])) & (df['תאריך'] <= pd.to_datetime(date_range[1]))]
    if source_filter:
        df = df[df['מקור'].isin(source_filter)]
    if category_filter:
        df = df[df['קטגוריה'].isin(category_filter)]

    st.dataframe(df.sort_values(by='תאריך', ascending=False), use_container_width=True)
