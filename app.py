import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import re

# --- הגדרות אבטחה ---
PASSWORD = "שנה_לסיסמה_שלך"

st.set_page_config(page_title="ארנק הקופונים החכם", layout="wide", page_icon="💰")

# פונקציה לבדיקת סיסמה
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 כניסה למערכת המאובטחת")
        pwd = st.text_input("הזן סיסמה:", type="password")
        if st.button("כניסה"):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("סיסמה שגויה")
        return False
    return True

# פונקציית עזר לחישוב סכומים (מטפלת בפורמטים כמו "50 x 5" או "100 ₪")
def parse_amount(val):
    try:
        val = str(val).replace('₪', '').strip()
        if 'x' in val.lower():
            parts = val.lower().split('x')
            return float(parts[0]) * float(parts[1])
        if '*' in val:
            parts = val.split('*')
            return float(parts[0]) * float(parts[1])
        # שליפת מספר בלבד (כולל נקודה עשרונית)
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
        return float(numbers[0]) if numbers else 0.0
    except:
        return 0.0

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = df.fillna("")
    except:
        st.error("שגיאה בחיבור ל-Google Sheets.")
        st.stop()

    st.title("💰 לוח בקרה וניהול קופונים")

    # --- חלק 1: ה-Dashboard (סיכום כספי) ---
    if not df.empty:
        total_value = df['סכום_או_מוצר'].apply(parse_amount).sum()
        num_coupons = len(df)
        
        # חישוב קופונים שפגים בקרוב (לוגיקה בסיסית)
        today = datetime.now()
        expiring_soon = 0
        for expiry in df['תוקף']:
            try:
                # מנסה לזהות פורמט DD-MM-YYYY או MM/YY
                if '-' in str(expiry):
                    exp_date = datetime.strptime(str(expiry), "%d-%m-%Y")
                    if 0 <= (exp_date - today).days <= 30:
                        expiring_soon += 1
            except:
                continue

        col1, col2, col3 = st.columns(3)
        col1.metric("סה\"כ שווי מוערך", f"{total_value:,.2f} ₪")
        col2.metric("קופונים במלאי", num_coupons)
        col3.metric("פגים ב-30 יום הקרובים", expiring_soon, delta_color="inverse")
        
        st.markdown("---")

    # --- חלק 2: תפריט ניהול ---
    st.sidebar.header("⚙️ אפשרויות")
    menu = st.sidebar.radio("פעולה:", ["צפייה וחיפוש", "הוספה ידנית", "טעינה מאקסל"])

    if menu == "הוספה ידנית":
        st.subheader("➕ הוספת קופון")
        with st.form("add_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                store = st.text_input("רשת")
                val = st.text_input("סכום (למשל: 100 או 50x5)")
                c_type = st.selectbox("סוג:", ["קוד/מספר", "לינק", "כרטיס עם CVV", "מוצר"])
            with col_b:
                code = st.text_input("קוד / לינק מלא")
                expiry = st.text_input("תוקף (DD-MM-YYYY)")
                cvv = st.text_input("CVV")
            notes = st.text_area("הערות")
            if st.form_submit_button("שמור"):
                new_row = pd.DataFrame([{"רשת": store, "סוג": c_type, "סכום_או_מוצר": val, 
                                          "קוד_או_לינק": code, "תוקף": expiry, "CVV": cvv, "הערות": notes}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("עודכן בגיליון!")
                st.rerun()

    elif menu == "טעינה מאקסל":
        st.subheader("📥 העלאה קבוצתית")
        file = st.file_uploader("בחר קובץ", type=['xlsx', 'csv'])
        if file:
            new_df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file)
            if st.button("בצע מיזוג לענן"):
                updated_df = pd.concat([df, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("הנתונים התווספו בהצלחה!")
                st.rerun()

    else: # צפייה וחיפוש
        search = st.text_input("🔍 חפש רשת או מוצר:")
        f_df = df[df['רשת'].str.contains(search, case=False, na=False)] if search else df

        for i, row in f_df.iterrows():
            with st.expander(f"**{row['רשת']}** | {row['סכום_או_מוצר']}"):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**תוקף:** {row['תוקף']}")
                    if row['CVV']: st.write(f"**CVV:** {row['CVV']}")
                    if row['הערות']: st.info(row['הערות'])
                with c2:
                    raw_code = str(row['קוד_או_לינק']).strip()
                    if raw_code.startswith("http"):
                        st.link_button("פתח קישור 🔗", raw_code)
                    else:
                        st.code(raw_code, language="text")
                if st.button(f"מחק קופון", key=f"del_{i}"):
                    updated_df = df.drop(i).reset_index(drop=True)
                    conn.update(worksheet="Sheet1", data=updated_df)
                    st.rerun()

    if st.sidebar.button("התנתק"):
        st.session_state.authenticated = False
        st.rerun()
