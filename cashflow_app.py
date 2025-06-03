 (cd "$(git rev-parse --show-toplevel)" && git apply --3way <<'EOF' 
diff --git a/cashflow_app.py b/cashflow_app.py
index e074eba7f23d2a195c85a0d48f060f8367dff23d..e5de711a1f0c483b20343f989d3254f7b66ccecb 100644
--- a/cashflow_app.py
+++ b/cashflow_app.py
@@ -1,67 +1,67 @@
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
 
 # שער המרה מדולר לשקל
 USD_TO_ILS = 3.8
 
 # בדיקה אם הקובץ קיים
 if not os.path.exists(CREDENTIALS_PATH):
+    # הודעת שגיאה אחידה המוצגת בעברית תקינה
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
-@@ -40,62 +43,65 @@ transactions = load_data(transactions_ws, transactions_cols)
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
 
EOF
)
