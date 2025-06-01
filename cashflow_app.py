import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="ניהול תזרים", layout="wide")

# --- Initialize session state to store data ---
if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame(columns=[
        'תאריך', 'סוג', 'סכום', 'מטבע', 'מקור', 'קטגוריה', 'תיאור']
    )

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
    df = st.session_state.transactions

    with st.expander("פילטרים"):
        col1, col2, col3 = st.columns(3)
        with col1:
            kind_filter = st.selectbox("סוג פעולה", ['הכל', 'הכנסה', 'הוצאה'])
        with col2:
            source_filter = st.selectbox("מקור", ['הכל', 'פיוניר', 'ישראלי'])
        with col3:
            month_filter = st.selectbox("חודש", ['הכל'] + list(df['תאריך'].dt.strftime('%Y-%m').unique()))

    filtered_df = df.copy()
    if kind_filter != 'הכל':
        filtered_df = filtered_df[filtered_df['סוג'] == kind_filter]
    if source_filter != 'הכל':
        filtered_df = filtered_df[filtered_df['מקור'] == source_filter]
    if month_filter != 'הכל':
        filtered_df = filtered_df[df['תאריך'].dt.strftime('%Y-%m') == month_filter]

    st.dataframe(filtered_df.sort_values(by='תאריך', ascending=False), use_container_width=True)

# --- Page: פעולות עתידיות ---
elif page == "פעולות עתידיות":
    st.title("📆 פעולות מתוכננות")
    st.info("ממשק זה ייבנה בהמשך – כולל תכנון לפי פרויקטים, תאריכים, והקצאות.")

# --- Page: פרויקטים ---
elif page == "פרויקטים":
    st.title("🚧 פרויקטים עתידיים")
    st.warning("ממשק הפרויקטים ייבנה לאחר סיום שלב בסיס התזרים.")
