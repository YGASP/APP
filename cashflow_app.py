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

# תפריט ניווט
st.sidebar.title("תפריט")
page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות", "תחזיות"])
st.sidebar.markdown("---")
if st.sidebar.button("📤 הוספה מהירה"):
    st.switch_page("הוספה")
if st.sidebar.button("ℹ️ קובץ עזרה"):
    st.info("👋 הכנס את ההכנסות וההוצאות שלך, נתח תחזיות, והישאר בשליטה על התזרים.")

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
    df_confirmed = df[df['סטטוס'] != 'תחזית']

    col1, col2, col3 = st.columns(3)
    with col1:
        p_in = df_confirmed[(df_confirmed['מקור'] == 'פיוניר') & (df_confirmed['סוג'] == 'הכנסה')]['סכום'].sum()
        p_out = df_confirmed[(df_confirmed['מקור'] == 'פיוניר') & (df_confirmed['סוג'] == 'הוצאה')]['סכום'].sum()
        st.metric("פיוניר", format_money(p_in - p_out, '$'))
    with col2:
        b_in = df_confirmed[(df_confirmed['מקור'] == 'ישראלי') & (df_confirmed['סוג'] == 'הכנסה')]['סכום'].sum()
        b_out = df_confirmed[(df_confirmed['מקור'] == 'ישראלי') & (df_confirmed['סוג'] == 'הוצאה')]['סכום'].sum()
        st.metric("ישראלי", format_money(b_in - b_out, '₪'))
    with col3:
        total = (p_in - p_out) * 3.8 + (b_in - b_out)
        st.metric("מאזן כולל (₪)", format_money(total, '₪'))

    st.subheader("📊 גרף חודשי - הכנסות/הוצאות")
    chart_data = df_confirmed.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    fig = px.bar(chart_data, x='חודש', y='סכום', color='סוג', barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🥧 פיזור לפי קטגוריה")
    pie_df = df_confirmed[df_confirmed['סוג'] == 'הוצאה'].groupby('קטגוריה')['סכום'].sum().reset_index()
    fig2 = px.pie(pie_df, names='קטגוריה', values='סכום', title='פיזור הוצאות')
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 השוואת חודשים (MoM)")
    pivot = df_confirmed.pivot_table(index='חודש', columns='סוג', values='סכום', aggfunc='sum').fillna(0).reset_index()
    if 'חודש' in pivot.columns:
        fig3 = px.line(pivot, x='חודש', y=['הכנסה', 'הוצאה'], markers=True)
        st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🏆 Top 5 קטגוריות הוצאה")
    top5 = df_confirmed[df_confirmed['סוג'] == 'הוצאה'].groupby('קטגוריה')['סכום'].sum().nlargest(5).reset_index()
    st.dataframe(top5)

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
            status = st.selectbox("סטטוס", ['אושר', 'תחזית'])

        submitted = st.form_submit_button("הוספה")
        if submitted:
            new_row = pd.DataFrame.from_records([{
                'תאריך': date.strftime('%Y-%m-%d'),
                'סוג': kind,
                'סכום': amount,
                'מטבע': currency,
                'מקור': source,
                'קטגוריה': category,
                'תיאור': description,
                'סטטוס': status
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

    with st.expander("🔍 סינון"):
        col1, col2, col3 = st.columns(3)
        with col1:
            start_date = st.date_input("מתאריך", value=df['תאריך'].min())
            end_date = st.date_input("עד תאריך", value=df['תאריך'].max())
        with col2:
            source_filter = st.multiselect("מקור", options=df['מקור'].unique(), default=df['מקור'].unique())
        with col3:
            category_filter = st.multiselect("קטגוריה", options=df['קטגוריה'].unique(), default=df['קטגוריה'].unique())

    mask = (df['תאריך'] >= pd.to_datetime(start_date)) & (df['תאריך'] <= pd.to_datetime(end_date)) & (df['מקור'].isin(source_filter)) & (df['קטגוריה'].isin(category_filter))
    st.dataframe(df[mask].sort_values(by='תאריך', ascending=False), use_container_width=True)

# ==========================================
# עמוד תחזיות
# ==========================================
elif page == "תחזיות":
    st.title("🔮 תחזיות עתידיות")
    df = transactions.copy()
    df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')
    forecasts = df[df['סטטוס'] == 'תחזית'].copy()

    st.subheader("📆 סינון לפי טווח תאריכים עתידיים")
    today = datetime.date.today()
    from_date = st.date_input("מתאריך", today)
    to_date = st.date_input("עד תאריך", today + datetime.timedelta(days=30))

    mask = (forecasts['תאריך'].dt.date >= from_date) & (forecasts['תאריך'].dt.date <= to_date)
    filtered_forecasts = forecasts[mask]
    st.dataframe(filtered_forecasts.sort_values(by='תאריך'), use_container_width=True)

    st.subheader("📈 גרף תחזיות")
    forecast_summary = filtered_forecasts.groupby(['תאריך', 'סוג'])['סכום'].sum().reset_index()
    if not forecast_summary.empty:
        fig = px.line(forecast_summary, x='תאריך', y='סכום', color='סוג', markers=True, title="תחזיות עתידיות")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("✅ אישור תחזיות")
    rows_to_update = st.multiselect("בחר תחזיות לאישור", filtered_forecasts.index.tolist())
    if st.button("אשר תחזיות שנבחרו"):
        transactions.loc[rows_to_update, 'סטטוס'] = 'אושר'
        save_data(transactions_ws, transactions)
        st.success("✨ התחזיות עודכנו כאושרו בהצלחה!")

    st.subheader("✏️ עריכת תחזית")
    row_to_edit = st.selectbox("בחר שורה לעריכה", options=filtered_forecasts.index.tolist())
    if row_to_edit is not None:
        row = filtered_forecasts.loc[row_to_edit]
        with st.form("edit_form"):
            new_date = st.date_input("תאריך", row['תאריך'].date())
            new_kind = st.selectbox("סוג", ['הכנסה', 'הוצאה'], index=['הכנסה', 'הוצאה'].index(row['סוג']))
            new_amount = st.number_input("סכום", value=float(row['סכום']), format="%.2f")
            new_currency = st.selectbox("מטבע", ['₪', '$'], index=['₪', '$'].index(row['מטבע']))
            new_source = st.selectbox("מקור", ['פיוניר', 'ישראלי'], index=['פיוניר', 'ישראלי'].index(row['מקור']))
            new_category = st.text_input("קטגוריה", row['קטגוריה'])
            new_description = st.text_input("תיאור נוסף", row['תיאור'])
            submitted = st.form_submit_button("שמור שינויים")
            if submitted:
                transactions.loc[row_to_edit] = [new_date, new_kind, new_amount, new_currency, new_source, new_category, new_description, 'תחזית']
                save_data(transactions_ws, transactions)
                st.success("✅ התחזית עודכנה בהצלחה!")
