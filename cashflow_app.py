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

# תפריט ניווט
st.sidebar.title("📁 תפריט ראשי")
page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות"])
st.sidebar.markdown("---")

# הוספה מהירה מהסיידבר
st.sidebar.markdown("### ➕ הוספה מהירה")
if st.sidebar.button("פתח טופס הוספה"):
    st.session_state.quick_add = True
else:
    st.session_state.quick_add = False

# קובץ עזרה
st.sidebar.markdown("---")
with st.sidebar.expander("📖 קובץ עזרה"):
    st.markdown("""
    - הוסף הוצאה/הכנסה דרך הטופס
    - ראה את התזרים החודשי בגרף
    - נהל לפי מקור, קטגוריה ותאריך
    - הנתונים נשמרים בגיליון Google Sheets
    """)

# תאריך, סכום וכו'
df = transactions.copy()
df['סכום'] = pd.to_numeric(df['סכום'], errors='coerce').fillna(0)
df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')
df['חודש'] = df['תאריך'].dt.to_period('M').astype(str)

# ==========================================
# עמוד חזית
# ==========================================
if page == "חזית":
    st.title("🌟 לוח בקרה – ניהול תזרים")

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

    # גרפים
    st.subheader("📊 תזרים חודשי – הכנסות והוצאות")
    chart_data = df.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    fig = px.bar(chart_data, x='חודש', y='סכום', color='סוג', barmode='group', title="הכנסות מול הוצאות")
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🧭 תזרים מצטבר")
    df_sorted = df.sort_values(by='תאריך')
    df_sorted['תזרים יומי'] = df_sorted.apply(lambda row: row['סכום'] if row['סוג'] == 'הכנסה' else -row['סכום'], axis=1)
    df_sorted['מאזן מצטבר'] = df_sorted['תזרים יומי'].cumsum()
    fig2 = px.line(df_sorted, x='תאריך', y='מאזן מצטבר', title="מאזן מצטבר לאורך זמן")
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📅 השוואת חודשים")
    month_compare = df.groupby(['חודש', 'סוג'])['סכום'].sum().unstack().fillna(0).reset_index()
    fig3 = px.line(month_compare, x='חודש', y=['הכנסה', 'הוצאה'], markers=True, title="השוואה חודשית")
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("🥧 פאי – קטגוריות הוצאה")
    pie_out = df[df['סוג'] == 'הוצאה'].groupby('קטגוריה')['סכום'].sum().reset_index()
    if not pie_out.empty:
        st.plotly_chart(px.pie(pie_out, names='קטגוריה', values='סכום', title="הוצאות לפי קטגוריה"), use_container_width=True)

    st.subheader("🥧 פאי – קטגוריות הכנסה")
    pie_in = df[df['סוג'] == 'הכנסה'].groupby('קטגוריה')['סכום'].sum().reset_index()
    if not pie_in.empty:
        st.plotly_chart(px.pie(pie_in, names='קטגוריה', values='סכום', title="הכנסות לפי קטגוריה"), use_container_width=True)

    st.subheader("📌 Top 5 קטגוריות הוצאה")
    top_out = pie_out.sort_values(by='סכום', ascending=False).head(5)
    st.table(top_out)

    st.subheader("📌 Top 5 קטגוריות הכנסה")
    top_in = pie_in.sort_values(by='סכום', ascending=False).head(5)
    st.table(top_in)

# ==========================================
# עמוד הוספה
# ==========================================
if page == "הוספה" or st.session_state.get("quick_add"):
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

    st.markdown("### 🔎 חיפוש וסינון")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        selected_source = st.selectbox("מקור", ['הכל'] + sorted(df['מקור'].dropna().unique().tolist()))
    with col2:
        selected_category = st.selectbox("קטגוריה", ['הכל'] + sorted(df['קטגוריה'].dropna().unique().tolist()))
    with col3:
        start_date = st.date_input("מתאריך", df['תאריך'].min())
    with col4:
        end_date = st.date_input("עד תאריך", df['תאריך'].max())

    df_filtered = df.copy()
    df_filtered = df_filtered[(df_filtered['תאריך'] >= pd.to_datetime(start_date)) & (df_filtered['תאריך'] <= pd.to_datetime(end_date))]
    if selected_source != 'הכל':
        df_filtered = df_filtered[df_filtered['מקור'] == selected_source]
    if selected_category != 'הכל':
        df_filtered = df_filtered[df_filtered['קטגוריה'] == selected_category]

    st.dataframe(df_filtered.sort_values(by='תאריך', ascending=False), use_container_width=True)
