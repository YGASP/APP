 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/cashflow_app.py b/cashflow_app.py
index e9809ce0940fa0fd642321cb53254700111618ce..0bfe9ff3c235ccf35976f94051fd9bc2711d7892 100644
--- a/cashflow_app.py
+++ b/cashflow_app.py
@@ -1,38 +1,41 @@
 import streamlit as st
 import pandas as pd
 import datetime
 import gspread
 import os
 from oauth2client.service_account import ServiceAccountCredentials
 
 # הגדרות עמוד
 st.set_page_config(page_title="ניהול תזרים", layout="wide")
 
 # קובץ ההרשאות
 CREDENTIALS_PATH = "credentials.json"
 
+# שער המרה מדולר לשקל
+USD_TO_ILS = 3.8
+
 # בדיקה אם הקובץ קיים
 if not os.path.exists(CREDENTIALS_PATH):
     st.error("⚠️ הקובץ credentials.json לא נמצא בתיקיית הפרויקט. העלה אותו ונסה שוב.")
     st.stop()
 
 # חיבור ל־Google Sheets
 scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
 creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_PATH, scope)
 client = gspread.authorize(creds)
 
 # מזהה הגיליון שלך
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
diff --git a/cashflow_app.py b/cashflow_app.py
index e9809ce0940fa0fd642321cb53254700111618ce..0bfe9ff3c235ccf35976f94051fd9bc2711d7892 100644
--- a/cashflow_app.py
+++ b/cashflow_app.py
@@ -40,62 +43,65 @@ transactions = load_data(transactions_ws, transactions_cols)
 # שמירת נתונים
 def save_data(ws, df):
     ws.clear()
     ws.update([df.columns.values.tolist()] + df.values.tolist())
 
 # תפריט ניווט
 st.sidebar.title("תפריט")
 page = st.sidebar.radio("עבור אל:", ["חזית", "הוספה", "רשומות"])
 
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
     st.title("🎯 ניהול תזרים")
 
     df = transactions.copy()
     df['סכום'] = pd.to_numeric(df['סכום'], errors='coerce').fillna(0)
+    df['amount_nis'] = df.apply(lambda r: r['סכום'] * USD_TO_ILS if r['מטבע'] == '$' else r['סכום'], axis=1)
 
     col1, col2, col3 = st.columns(3)
     with col1:
-        p_in = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הכנסה')]['סכום'].sum()
-        p_out = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הוצאה')]['סכום'].sum()
+        p_in = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הכנסה') & (df['מטבע'] == '$')]['סכום'].sum()
+        p_out = df[(df['מקור'] == 'פיוניר') & (df['סוג'] == 'הוצאה') & (df['מטבע'] == '$')]['סכום'].sum()
         st.metric("פיוניר", format_money(p_in - p_out, '$'))
     with col2:
-        b_in = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הכנסה')]['סכום'].sum()
-        b_out = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הוצאה')]['סכום'].sum()
+        b_in = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הכנסה') & (df['מטבע'] == '₪')]['סכום'].sum()
+        b_out = df[(df['מקור'] == 'ישראלי') & (df['סוג'] == 'הוצאה') & (df['מטבע'] == '₪')]['סכום'].sum()
         st.metric("ישראלי", format_money(b_in - b_out, '₪'))
     with col3:
-        total = (p_in - p_out)*3.8 + (b_in - b_out)
+        total_income = df[df['סוג'] == 'הכנסה']['amount_nis'].sum()
+        total_expense = df[df['סוג'] == 'הוצאה']['amount_nis'].sum()
+        total = total_income - total_expense
         st.metric("מאזן כולל (₪)", format_money(total, '₪'))
 
 # ==========================================
 # עמוד הוספה
 # ==========================================
 elif page == "הוספה":
     st.title("📥 הוספת הכנסה / הוצאה")
 
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
 
EOF
)
