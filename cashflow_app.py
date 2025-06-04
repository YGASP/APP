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

# עיצוב כספים
def format_money(val, currency):
    try:
        val = float(val)
        return "{:,.2f} {}".format(val, currency)
    except:
        return f"{val} {currency}"

# Sidebar – ניווט + פעולות מהירות
st.sidebar.title("תפריט")
page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות"])

# כפתור הוספה מהירה
if st.sidebar.button("➕ הוספה מהירה"):
    st.session_state.page = "הוספה"

# קובץ עזרה
with st.sidebar.expander("📘 עזרה והנחיות"):
    st.markdown("""
    - הזן הכנסה או הוצאה לפי תאריך, מקור וקטגוריה.
    - תוכל לראות את כל הנתונים ב'רשומות'.
    - גרפים נמצאים ב'חזית'.
    - כל שינוי נשמר אוטומטית לגיליון Google Sheets שלך.
    """)

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

    st.subheader("📊 גרף חודשי: הכנסות / הוצאות")
    chart_data = df.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    fig = px.bar(chart_data, x='חודש', y='סכום', color='סוג', barmode='group', title="תזרים לפי חודשים")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🎯 התפלגות לפי קטגוריה (גרף פאי)")
    pie_data = df.groupby(['קטגוריה', 'סוג'])['סכום'].sum().reset_index()
    pie_tab1, pie_tab2 = st.tabs(["הוצאות", "הכנסות"])
    with pie_tab1:
        pie1 = pie_data[pie_data['סוג'] == 'הוצאה']
        fig1 = px.pie(pie1, names='קטגוריה', values='סכום', title="התפלגות הוצאות")
        st.plotly_chart(fig1, use_container_width=True)
    with pie_tab2:
        pie2 = pie_data[pie_data['סוג'] == 'הכנסה']
        fig2 = px.pie(pie2, names='קטגוריה', values='סכום', title="התפלגות הכנסות")
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 תזרים מצטבר לאורך זמן")
    df_sorted = df.sort_values('תאריך')
    df_sorted['מאזן יומי'] = df_sorted.apply(lambda row: row['סכום'] if row['סוג'] == 'הכנסה' else -row['סכום'], axis=1)
    df_sorted['מאזן מצטבר'] = df_sorted['מאזן יומי'].cumsum()
    fig_cum = px.line(df_sorted, x='תאריך', y='מאזן מצטבר', title="מאזן מצטבר לאורך זמן")
    st.plotly_chart(fig_cum, use_container_width=True)

    st.subheader("🔁 השוואה חודשית")
    month_compare_raw = df.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    month_compare = month_compare_raw.pivot(index='חודש', columns='סוג', values='סכום').fillna(0).reset_index()
    fig3 = px.line(month_compare, x='חודש', y=['הכנסה', 'הוצאה'], markers=True, title="השוואה חודשית")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("💸 Top 5 קטגוריות הוצאה")
    top5 = pie1.sort_values('סכום', ascending=False).head(5)
    st.dataframe(top5[['קטגוריה', 'סכום']], use_container_width=True)

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

    st.subheader("🔎 סינון")
    col1, col2, col3 = st.columns(3)
    with col1:
        date_range = st.date_input("טווח תאריכים", [])
    with col2:
        source_filter = st.selectbox("מקור", ['הכל'] + df['מקור'].unique().tolist())
    with col3:
        category_filter = st.text_input("חיפוש לפי קטגוריה")

    filtered = df
    if len(date_range) == 2:
        filtered = filtered[(filtered['תאריך'] >= pd.to_datetime(date_range[0])) & (filtered['תאריך'] <= pd.to_datetime(date_range[1]))]
    if source_filter != 'הכל':
        filtered = filtered[filtered['מקור'] == source_filter]
    if category_filter:
        filtered = filtered[filtered['קטגוריה'].str.contains(category_filter, case=False, na=False)]

    st.dataframe(filtered.sort_values(by='תאריך', ascending=False), use_container_width=True)
