import streamlit as st
import pandas as pd
import datetime
import gspread
import os
import json
import plotly.express as pxכ
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

# תפריט תחזית לפי מכירות ורווח ליחידה
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
            total_forecast = round(units * profit_per_unit, 2)

            new_row = {
                'תאריך': forecast_month.strftime('%Y-%m-01'),
                'סוג': 'הכנסה',
                'סכום': total_forecast,
                'מטבע': '$',
                'מקור': 'פיוניר',
                'קטגוריה': f"מכירות {sku}",
                'תיאור': f"צפי רווח לפי {units} יחידות",
                'סטטוס': 'תחזית'
            }

            new_df = pd.DataFrame([new_row])
            transactions = pd.concat([transactions, new_df], ignore_index=True)
            save_data(transactions_ws, transactions)
            st.success(f"✅ תחזית נרשמה: {units} יחידות × ${profit_per_unit:.2f} = ${total_forecast:.2f}")

# תפריט ניווט
st.sidebar.title("תפריט")
page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות", "תחזיות"])

# תפריט הוספה מהירה - טופס צדדי
with st.sidebar.expander("📤 הוספה מהירה", expanded=False):
    with st.form("quick_add_form"):
        date = st.date_input("תאריך", datetime.date.today(), key="quick_date")
        kind = st.selectbox("סוג", ['הכנסה', 'הוצאה'], key="quick_kind")
        amount = st.number_input("סכום", min_value=0.0, format="%.2f", key="quick_amount")
        fee = st.number_input("עמלת העברה", min_value=0.0, format="%.2f", key="quick_fee")
        currency = st.selectbox("מטבע", ['₪', '$'], key="quick_currency")
        source = st.selectbox("מקור", ['פיוניר', 'ישראלי'], key="quick_source")
        category = st.text_input("קטגוריה", key="quick_category")
        description = st.text_input("תיאור", key="quick_description")
        status = st.selectbox("סטטוס", ['אושר', 'תחזית'], key="quick_status")
        quick_submitted = st.form_submit_button("הוסף תנועה")

        if quick_submitted:
            new_rows = [{
                'תאריך': date.strftime('%Y-%m-%d'),
                'סוג': kind,
                'סכום': amount,
                'מטבע': currency,
                'מקור': source,
                'קטגוריה': category,
                'תיאור': description,
                'סטטוס': status
            }]
            if fee > 0:
                new_rows.append({
                    'תאריך': date.strftime('%Y-%m-%d'),
                    'סוג': 'הוצאה',
                    'סכום': fee,
                    'מטבע': currency,
                    'מקור': source,
                    'קטגוריה': 'עמלה',
                    'תיאור': 'עמלת העברה',
                    'סטטוס': status
                })
            new_df = pd.DataFrame(new_rows)
            transactions = pd.concat([transactions, new_df], ignore_index=True)
            save_data(transactions_ws, transactions)
            st.success("✅ נוסף בהצלחה!")

# עיצוב סכומים
def format_money(val, currency):
    try:
        val = float(val)
        return "{:,.2f} {}".format(val, currency)
    except:
        return f"{val} {currency}"
# ============================
# עמוד חזית
# ============================
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

    st.subheader("📊 גרף חודשי")
    chart_data = df_confirmed.groupby(['חודש', 'סוג'])['סכום'].sum().reset_index()
    fig = px.bar(chart_data, x='חודש', y='סכום', color='סוג', barmode='group')
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("🥧 פיזור לפי קטגוריה")
    pie_df = df_confirmed[df_confirmed['סוג'] == 'הוצאה'].groupby('קטגוריה')['סכום'].sum().reset_index()
    fig2 = px.pie(pie_df, names='קטגוריה', values='סכום')
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("📈 השוואת חודשים")
    pivot = df_confirmed.pivot_table(index='חודש', columns='סוג', values='סכום', aggfunc='sum').fillna(0).reset_index()
    if 'חודש' in pivot.columns:
        fig3 = px.line(pivot, x='חודש', y=['הכנסה', 'הוצאה'], markers=True)
        st.plotly_chart(fig3, use_container_width=True)

# ============================
# עמוד הוספה רגילה
# ============================
elif page == "הוספה":
    st.title("🗓 הוספת תנועה")
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
            fee = st.number_input("עמלת העברה", min_value=0.0, format="%.2f")

        submitted = st.form_submit_button("הוספה")
        if submitted:
            new_rows = [{
                'תאריך': date.strftime('%Y-%m-%d'),
                'סוג': kind,
                'סכום': amount,
                'מטבע': currency,
                'מקור': source,
                'קטגוריה': category,
                'תיאור': description,
                'סטטוס': status
            }]
            if fee > 0:
                new_rows.append({
                    'תאריך': date.strftime('%Y-%m-%d'),
                    'סוג': 'הוצאה',
                    'סכום': fee,
                    'מטבע': currency,
                    'מקור': source,
                    'קטגוריה': 'עמלה',
                    'תיאור': 'עמלת העברה',
                    'סטטוס': status
                })
            new_df = pd.DataFrame(new_rows)
            transactions = pd.concat([transactions, new_df], ignore_index=True)
            save_data(transactions_ws, transactions)
            st.success("✅ נשמר בהצלחה!")

# ============================
# עמוד רשומות
# ============================
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
            source_filter = st.multiselect("מקור", df['מקור'].unique(), default=df['מקור'].unique())
        with col3:
            category_filter = st.multiselect("קטגוריה", df['קטגוריה'].unique(), default=df['קטגוריה'].unique())

    mask = (df['תאריך'] >= pd.to_datetime(start_date)) & (df['תאריך'] <= pd.to_datetime(end_date)) & (df['מקור'].isin(source_filter)) & (df['קטגוריה'].isin(category_filter))
    st.dataframe(df[mask].sort_values(by='תאריך', ascending=False), use_container_width=True)

# ============================
# ============================
# ============================
# ============================
# עמוד תחזיות
# ============================
elif page == "תחזיות":
    st.title("🔮 תחזיות עתידיות")
    df = transactions.copy()
    df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')
    forecasts = df[df['סטטוס'] == 'תחזית'].copy()
    approved = df[df['סטטוס'] == 'אושר'].copy()

    st.subheader("✅ אישור תחזיות שהתממשו בפועל")
    forecast_df = forecasts.copy()
    forecast_df['אישור'] = False

    if not forecast_df.empty:
        edited_df = st.data_editor(
            forecast_df[['תאריך', 'סכום', 'מטבע', 'מקור', 'קטגוריה', 'תיאור', 'אישור']],
            use_container_width=True,
            key="forecast_approval_editor"
        )

        if st.button("📥 עדכן תחזיות שאושרו"):
            approved_indexes = edited_df[edited_df['אישור']].index
            transactions.loc[approved_indexes, 'סטטוס'] = 'אושר'
            save_data(transactions_ws, transactions)
            st.success(f"עודכנו {len(approved_indexes)} תחזיות כמאושרות")
    else:
        st.info("אין תחזיות לאישור כרגע.")

    st.subheader("📆 טווח תאריכים")
    today = datetime.date.today()
    from_date = st.date_input("מתאריך", today)
    to_date = st.date_input("עד תאריך", today + datetime.timedelta(days=30))

    mask = (df['תאריך'].dt.date >= from_date) & (df['תאריך'].dt.date <= to_date)
    forecasted = df[mask & (df['סטטוס'].isin(['תחזית', 'אושר']))].copy()

    st.subheader("📈 גרף תחזית מול בפועל")
    forecasted['label'] = forecasted['סטטוס'] + ' - ' + forecasted['קטגוריה']
    forecasted_summary = forecasted.groupby(['תאריך', 'label'])['סכום'].sum().reset_index()
if not forecasted_summary.empty:
    fig = px.bar(forecasted_summary, x='תאריך', y='סכום', color='label', barmode='group', text='סכום')
    fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
    fig.update_layout(xaxis_title='תאריך', yaxis_title='סכום', legend_title='סוג תחזית')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("אין נתונים לגרף")

    st.subheader("🧾 טבלת תחזיות")
    st.dataframe(forecasted.sort_values(by='תאריך'), use_container_width=True)

    st.subheader("✏️ עריכת תחזית")
    editable_forecasts = forecasted[forecasted['סטטוס'] == 'תחזית']
    if not editable_forecasts.empty:
        row_to_edit = st.selectbox("בחר שורה לעריכה", options=editable_forecasts.index.tolist())
        row = editable_forecasts.loc[row_to_edit]
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
                st.success("✅ התחזית עודכנה!")

    st.subheader("📊 עדכון סכום בפועל / דחיית תחזית")
    editable_df = forecasts.copy()
    if not editable_df.empty:
        selected_index = st.selectbox("בחר תחזית לעדכון:", editable_df.index, format_func=lambda i: f"{editable_df.at[i, 'תאריך']} | {editable_df.at[i, 'קטגוריה']} | ${editable_df.at[i, 'סכום']}")
        selected_row = editable_df.loc[selected_index]

        st.markdown(f"### ✏️ תחזית נבחרת: {selected_row['קטגוריה']} בתאריך {selected_row['תאריך']}")
        actual_value = st.number_input("💰 כמה באמת התקבל?", min_value=0.0, format="%.2f", value=selected_row['סכום'])
        status = st.selectbox("🟢 מה הסטטוס?", ["אושר", "נדחה"])

        if st.button("💾 שמור עדכון"):
            original_value = selected_row['סכום']
            transactions.at[selected_index, 'סכום'] = actual_value
            transactions.at[selected_index, 'סטטוס'] = status
            transactions.at[selected_index, 'תיאור'] += f" | סכום צפוי: ${original_value:.2f} | בפועל: ${actual_value:.2f}"
            save_data(transactions_ws, transactions)
            st.success(f"התחזית עודכנה כ־{status} עם סכום בפועל: ${actual_value:.2f}")
    else:
        st.info("אין תחזיות לעדכון כרגע.")
