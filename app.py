import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re
from datetime import datetime, timedelta

# --- 1. הגדרות עיצוב גלובליות ---
PASSWORD = "1"
GLOBAL_FONT_SIZE = "20px"  # <--- שנה כאן את גודל הפונט לכל המלל (למשל "18px", "22px" וכו')
GLOBAL_FONT_SIZE = "20px" 

# מילון לוגואים - הוסף כאן שמות רשתות וקישורים ללוגו (URL)
# מילון לוגואים
LOGOS = {
    "רמי לוי": "https://upload.wikimedia.org/wikipedia/he/thumb/6/6a/Rami_Levy_logo.svg/250px-Rami_Levy_logo.svg.png",
    "שופרסל": "https://upload.wikimedia.org/wikipedia/he/thumb/3/30/Shufersal_logo.svg/250px-Shufersal_logo.svg.png",
    "רמי לוי": "https://he.wikipedia.org/wiki/%D7%A8%D7%9E%D7%99_%D7%9C%D7%95%D7%99_%D7%A9%D7%99%D7%95%D7%95%D7%A7_%D7%94%D7%A9%D7%A7%D7%9E%D7%94#/media/%D7%A7%D7%95%D7%91%D7%A5:RAMILEVI.png",
    "Dream Card": "https://www.just4u.co.il/Pictures/12621111.jpg",
"ויקטורי": "https://upload.wikimedia.org/wikipedia/he/c/c9/Victory_Supermarket_Chain_Logo.png",
    # ניתן להוסיף עוד רשתות...
}
DEFAULT_LOGO = "https://cdn-icons-png.flaticon.com/512/726/726476.png" # אייקון קופון גנרי
DEFAULT_LOGO = "https://cdn-icons-png.flaticon.com/512/726/726476.png"

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

# --- הזרקת CSS לשליטה גלובלית בגודל הפונט ---
# הזרקת CSS (כולל גודל פונט ואופטימיזציה לכפתורי הכיווץ)
st.markdown(f"""
   <style>
   html, body, [class*="st-"], p, div, span, input, label, button {{
       font-size: {GLOBAL_FONT_SIZE} !important;
   }}
    /* התאמה ספציפית לקוד כדי שלא יהיה קטן מדי */
    code {{
        font-size: {GLOBAL_FONT_SIZE} !important;
    }}
    /* הגדלת כותרות ה-Expander */
    .st-emotion-cache-p3m962 {{ 
        font-size: {GLOBAL_FONT_SIZE} !important;
    }}
    code {{ font-size: {GLOBAL_FONT_SIZE} !important; }}
   </style>
   """, unsafe_allow_html=True)

@@ -109,7 +101,7 @@

st.title("🎫 My Coupon Wallet")

    # --- מדדים ---
    # מדדים
if not df.empty:
total_value = df['value'].apply(parse_amount).sum()
c1, c2, c3 = st.columns(3)
@@ -139,7 +131,23 @@
st.success("נשמר!"); st.rerun()

elif action == "הארנק שלי":
        # --- הגדרת מצב כיווץ/הרחבה ב-Session State ---
        if "all_expanded" not in st.session_state:
            st.session_state.all_expanded = True # ברירת מחדל פתוח

search = st.text_input("🔍 חיפוש רשת...")
        
        # כפתורי שליטה גלובליים
        col_exp1, col_exp2, _ = st.columns([1, 1, 4])
        if col_exp1.button("📂 הרחב הכל", use_container_width=True):
            st.session_state.all_expanded = True
            st.rerun()
        if col_exp2.button("📁 כווץ הכל", use_container_width=True):
            st.session_state.all_expanded = False
            st.rerun()

        st.markdown("---")

df['temp_date'] = df['expiry'].apply(parse_expiry)
display_df = df.sort_values(by='temp_date', ascending=True)
if search:
@@ -151,15 +159,11 @@
networks = display_df['network'].unique()
for net in networks:
net_coupons = display_df[display_df['network'] == net]
                
                # בחירת לוגו
logo_url = LOGOS.get(net, DEFAULT_LOGO)

                # כותרת אקספנדר עם לוגו קטן ושם מודגש
                with st.expander(f"🏢 **{net.upper()}** — ({len(net_coupons)} פריטים)", expanded=True):
                    # הצגת לוגו הרשת בראש הרשימה
                # השינוי כאן: expanded מקבל את הערך מה-Session State
                with st.expander(f"🏢 **{net.upper()}** — ({len(net_coupons)} פריטים)", expanded=st.session_state.all_expanded):
st.image(logo_url, width=80)
                    
for i, row in net_coupons.iterrows():
expiry_date = parse_expiry(row['expiry'])
bg_color = "#F8F9FA"
