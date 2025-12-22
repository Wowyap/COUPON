import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# ... (הפונקציות הקודמות check_password, clean_decimal_strings, parse_amount נשארות אותו דבר) ...

# --- פונקציית העריכה החדשה ---
@st.dialog("ערוך קופון ✏️")
def edit_coupon_dialog(index, row_data, df, conn):
    st.write(f"מעדכן קופון עבור: **{row_data['network']}**")
    
    with st.form("edit_form"):
        new_net = st.text_input("רשת", value=row_data['network'])
        new_val = st.text_input("ערך", value=row_data['value'])
        new_type = st.selectbox("סוג", ["Link", "Code", "Credit Card"], 
                               index=["Link", "Code", "Credit Card"].index(row_data['type']) if row_data['type'] in ["Link", "Code", "Credit Card"] else 0)
        new_code = st.text_input("קוד או קישור", value=row_data['code_or_link'])
        new_exp = st.text_input("תוקף", value=row_data['expiry'])
        new_cvv = st.text_input("CVV", value=row_data['cvv'])
        new_notes = st.text_area("הערות", value=row_data['notes'])
        
        if st.form_submit_button("שמור שינויים"):
            # עדכון השורה ב-DataFrame
            df.at[index, 'network'] = new_net
            df.at[index, 'value'] = new_val
            df.at[index, 'type'] = new_type
            df.at[index, 'code_or_link'] = new_code
            df.at[index, 'expiry'] = new_exp
            df.at[index, 'cvv'] = new_cvv
            df.at[index, 'notes'] = new_notes
            
            # שליחה לגוגל שיטס
            conn.update(worksheet="Sheet1", data=df)
            st.success("הקופון עודכן בהצלחה!")
            st.rerun()

# --- החלק של תצוגת הקופונים (My Wallet) בתוך ה-else הראשי ---
# (אני כותב כאן רק את השינוי בתוך הלופ של הקופונים)

# ... בתוך הלופ שבו מציגים את הקופונים:
for i, row in net_coupons.iterrows():
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 2, 0.6]) # הרחבתי מעט את עמודת הכפתורים
        
        with c1:
            st.markdown(f"### {row['value']} ₪")
            if row['expiry']: st.caption(f"📅 Expires: {row['expiry']}")
            if row['cvv']: st.markdown(f"**CVV:** `{row['cvv']}`")
        
        with c2:
            val = str(row['code_or_link']).strip()
            if val.startswith("http"):
                st.link_button("🌐 Open Link", val, use_container_width=True)
            else:
                st.code(val, language="text")
            if row['notes']: st.caption(f"📝 {row['notes']}")
        
        with c3:
            # כפתור עריכה
            if st.button("✏️", key=f"edit_{i}", help="Edit coupon", use_container_width=True):
                edit_coupon_dialog(i, row, df, conn)
            
            # כפתור מחיקה
            if st.button("🗑️", key=f"del_{i}", help="Delete coupon", use_container_width=True):
                full_df = conn.read(worksheet="Sheet1", ttl="0")
                full_df = full_df.drop(i).reset_index(drop=True)
                conn.update(worksheet="Sheet1", data=full_df)
                st.rerun()
