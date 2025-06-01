import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="ניהול תזרים", layout="wide")

# --- Initialize session state to store data ---
if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame(columns=[
        'תאריך', 'סוג', 'סכום', 'מטבע', 'מקור', 'קטגוריה', 'תיאור']
    )

if 'planned' not in st.session_state:
    st.session_state.planned = pd.DataFrame(columns=['תאריך', 'סכום', 'תיאור'])

if 'projects' not in st.session_state:
    st.session_state.projects = pd.DataFrame(columns=['שם פרויקט', 'הוצאה מתוכננת', 'הוצאה בפועל'])

# --- Sidebar Navigation ---
st.sidebar.title("תפריט")
page = st.sidebar.radio("עבור אל:", ["חזית", "רשומות", "פעולות עתידיות", "פרויקטים"])

# --- Utility Function ---
def format_money(amount, currency):
    return f"{amount:,.2f} {currency}"

# --- Page: חזית ---
if page == "חזית":
    st.title("🎯 ניהול תזרים")
    
    df = st.session_state.transactions

    col1, col2, col3 = st.columns(3)
    with col1:
        payoneer_sum = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הכנסה')]['סכום'].sum()
        payoneer_exp = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הוצאה')]['סכום'].sum()
        st.metric("פיוניר", format_money(payoneer_sum - payoneer_exp, '$'))
    with col2:
        bank_sum = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הכנסה')]['סכום'].sum()
        bank_exp = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הוצאה')]['סכום'].sum()
        st.metric("ישראלי", format_money(bank_sum - bank_exp, '₪'))
    with col3:
        total = (payoneer_sum - payoneer_exp)*3.8 + (bank_sum - bank_exp)  # conversion to NIS
        st.metric("מאזן כולל (₪)", format_money(total, '₪'))

    st.subheader("📥 הוספת הכנסה / הוצאה")
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
            st.session_state.transactions = pd.concat([
                st.session_state.transactions,
                pd.DataFrame.from_records([{
                    'תאריך': date,
                    'סוג': kind,
                    'סכום': amount,
                    'מטבע': currency,
                    'מקור': source,
                    'קטגוריה': category,
                    'תיאור': description
                }])
            ], ignore_index=True)
            st.success("הרשומה נוספה בהצלחה ✅")

# --- Page: רשומות ---
elif page == "רשומות":
    st.title("📒 כל הרשומות")
    df = st.session_state.transactions.copy()
    df['תאריך'] = pd.to_datetime(df['תאריך'], errors='coerce')

    with st.expander("פילטרים"):
        col1, col2, col3 = st.columns(3)
        with col1:
            kind_filter = st.selectbox("סוג פעולה", ['הכל', 'הכנסה', 'הוצאה'])
        with col2:
            source_filter = st.selectbox("מקור", ['הכל', 'פיוניר', 'ישראלי'])
        with col3:
            month_filter = st.selectbox("חודש", ['הכל'] + list(df['תאריך'].dropna().dt.strftime('%Y-%m').unique()))

    filtered_df = df.copy()
    if kind_filter != 'הכל':
        filtered_df = filtered_df[filtered_df['סוג'] == kind_filter]
    if source_filter != 'הכל':
        filtered_df = filtered_df[filtered_df['מקור'] == source_filter]
    if month_filter != 'הכל':
        filtered_df = filtered_df[filtered_df['תאריך'].dt.strftime('%Y-%m') == month_filter]

    st.dataframe(filtered_df.sort_values(by='תאריך', ascending=False), use_container_width=True)

# --- Page: פעולות עתידיות ---
elif page == "פעולות עתידיות":
    st.title("📆 פעולות עתידיות")

    with st.form("planned_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            p_date = st.date_input("תאריך מתוכנן", datetime.date.today())
        with col2:
            p_amount = st.number_input("סכום מתוכנן", min_value=0.0, format="%.2f")
        with col3:
            p_desc = st.text_input("תיאור")
        submit_plan = st.form_submit_button("הוסף תכנון")

        if submit_plan:
            st.session_state.planned = pd.concat([
                st.session_state.planned,
                pd.DataFrame.from_records([{
                    'תאריך': p_date,
                    'סכום': p_amount,
                    'תיאור': p_desc
                }])
            ], ignore_index=True)
            st.success("הפעולה נוספה לתכנון ✅")

    st.subheader("רשימת פעולות עתידיות")
    st.dataframe(st.session_state.planned.sort_values(by='תאריך'), use_container_width=True)

# --- Page: פרויקטים ---
elif page == "פרויקטים":
    st.title("🚧 פרויקטים")

    with st.form("project_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            project_name = st.text_input("שם פרויקט")
        with col2:
            planned_budget = st.number_input("הוצאה מתוכננת", min_value=0.0, format="%.2f")
        with col3:
            actual_spent = st.number_input("הוצאה בפועל", min_value=0.0, format="%.2f")
        submit_proj = st.form_submit_button("הוסף פרויקט")

        if submit_proj:
            st.session_state.projects = pd.concat([
                st.session_state.projects,
                pd.DataFrame.from_records([{
                    'שם פרויקט': project_name,
                    'הוצאה מתוכננת': planned_budget,
                    'הוצאה בפועל': actual_spent
                }])
            ], ignore_index=True)
            st.success("הפרויקט נוסף ✅")

    st.subheader("רשימת פרויקטים")
    st.dataframe(st.session_state.projects, use_container_width=True)
