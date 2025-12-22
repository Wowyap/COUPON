import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
import re

# --- הגדרות אבטחה ועיצוב ---
PASSWORD = "7341756"

st.set_page_config(page_title="ארנק הקופונים החכם", layout="wide", page_icon="💰")

# פונקציה להזרקת CSS עבור גודל גופן ולוגואים
def apply_custom_style(font_size):
    st.markdown(f"""
        <style>
            html, body, [class*="st-"] {{
                font-size: {font_size}px !important;
            }}
            .coupon-card {{
                border: 1px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                margin-bottom: 10px;
                background-color: #f9f9f9;
            }}
            .logo-img {{
                max-width: 80px;
                border-radius: 5px;
            }}
        </style>
    """, unsafe_allow_html=True)

# פונקציה להצגת לוגו לפי שם רשת (באמצעות Clearbit API בחינם)
def get_logo(store_name):
    clean_name = store_name.lower().replace(" ", "")
    # ניתן להוסיף כאן לוגואים ספציפיים אם יש לך קישורים קבועים
    return f"https://logo.clearbit.com/{clean_name}.co.il"

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

# פונקציית עזר לחישוב סכומים
def parse_amount(val):
    try:
        val = str(val).replace('₪', '').strip()
        if 'x' in val.lower():
            parts = val.lower().split('x')
            return float(parts[0]) * float(parts[1])
        if '*' in val:
            parts = val.split('*')
            return float(parts[0]) * float(parts[1])
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
        return float(numbers[0]) if numbers else 0.0
    except:
        return 0.0

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # הגדרות עיצוב ב-Sidebar
    st.sidebar.header("🎨 עיצוב ותצוגה")
    font_size = st.sidebar.slider("גודל גופן כללי", 12, 24, 16)
    apply_custom_style(font_size)

    try:
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = df.fillna("")
        # הוספת עמודת סטטוס אם אינה קיימת
        if 'סטטוס' not in df.columns:
            df['סטטוס'] = 'פעיל'
    except Exception as e:
        st.error(f"שגיאה בחיבור: {e}")
        st.stop()

    st.title("💰 ניהול קופונים חכם")

    # --- Dashboard (רק לקופונים פעילים) ---
    active_df = df[df['סטטוס'] == 'פעיל']
    
    if not active_df.empty:
        total_value = active_df['סכום_או_מוצר'].apply(parse_amount).sum()
        num_coupons = len(active_df)
        
        col1, col2, col3 = st.columns(3)
        col1.metric("סה\"כ שווי פעיל", f"{total_value:,.2f} ₪")
        col2.metric("קופונים במלאי", num_coupons)
        col3.metric("נוצלו עד כה", len(df[df['סטטוס'] == 'נוצל']))
        st.markdown("---")

    menu = st.sidebar.radio("ניווט:", ["קופונים פעילים", "ארכיון (נוצלו)", "הוספה חדשה", "טעינה קבוצתית"])

    if menu == "הוספה חדשה":
        st.subheader("➕ הוספת קופון חדש")
        with st.form("add_form"):
            col_a, col_b = st.columns(2)
            with col_a:
                store = st.text_input("רשת (למשל: Shufersal, Fox)")
                val = st.text_input("סכום (100 או 50x5)")
                c_type = st.selectbox("סוג:", ["קוד/מספר", "לינק", "כרטיס", "מוצר"])
            with col_b:
                code = st.text_input("קוד / לינק")
                expiry = st.text_input("תוקף (DD-MM-YYYY)")
                cvv = st.text_input("CVV")
            notes = st.text_area("הערות")
            if st.form_submit_button("שמור קופון"):
                new_row = pd.DataFrame([{
                    "רשת": store, "סוג": c_type, "סכום_או_מוצר": val, 
                    "קוד_או_לינק": code, "תוקף": expiry, "CVV": cvv, 
                    "הערות": notes, "סטטוס": "פעיל"
                }])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("נשמר בהצלחה!")
                st.rerun()

    elif menu == "קופונים פעילים" or menu == "ארכיון (נוצלו)":
        current_status = "פעיל" if menu == "קופונים פעילים" else "נוצל"
        search = st.text_input("🔍 חיפוש רשת:", "")
        
        display_df = df[df['סטטוס'] == current_status]
        if search:
            display_df = display_df[display_df['רשת'].str.contains(search, case=False, na=False)]

        if display_df.empty:
            st.info("אין קופונים להצגה.")
        
        for i, row in display_df.iterrows():
            with st.container():
                # יצירת מבנה כרטיס
                c1, c2, c3 = st.columns([1, 4, 2])
                
                with c1: # לוגו
                    logo_url = get_logo(row['רשת'])
                    st.image(logo_url, width=60) # הלוגו נמשך אוטומטית לפי שם הרשת
                
                with c2: # פרטים
                    st.markdown(f"### {row['רשת']} | {row['סכום_או_מוצר']}")
                    st.caption(f"תוקף: {row['תוקף']} | סוג: {row['סוג']}")
                    if row['הערות']: st.write(f"📝 {row['הערות']}")
                
                with c3: # פעולות
                    raw_code = str(row['קוד_או_לינק']).strip()
                    if raw_code.startswith("http"):
                        st.link_button("פתח קישור 🔗", raw_code)
                    else:
                        st.code(raw_code, language="text")
                    
                    # כפתור שינוי סטטוס
                    if current_status == "פעיל":
                        if st.button(f"✅ סמן כנוצל", key=f"use_{i}"):
                            df.at[i, 'סטטוס'] = 'נוצל'
                            conn.update(worksheet="Sheet1", data=df)
                            st.rerun()
                    else:
                        if st.button(f"⏪ החזר לפעיל", key=f"reactivate_{i}"):
                            df.at[i, 'סטטוס'] = 'פעיל'
                            conn.update(worksheet="Sheet1", data=df)
                            st.rerun()
                    
                    if st.button(f"🗑️ מחק לצמיתות", key=f"del_{i}"):
                        df = df.drop(i).reset_index(drop=True)
                        conn.update(worksheet="Sheet1", data=df)
                        st.rerun()
                st.markdown("---")

    if st.sidebar.button("התנתק"):
        st.session_state.authenticated = False
        st.rerun()
