import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# --- הגדרות אבטחה ---
PASSWORD = "שנה_לסיסמה_שלך"

st.set_page_config(page_title="ארנק הקופונים שלי", layout="wide", page_icon="🎫")

# פונקציה לבדיקת סיסמה
def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 כניסה למערכת")
        pwd = st.text_input("הזן סיסמה:", type="password")
        if st.button("כניסה"):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("סיסמה שגויה")
        return False
    return True

if check_password():
    # חיבור לגוגל שיטס
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # טעינת נתונים
    try:
        # ttl="0" מבטיח שהנתונים יתעדכנו מיד ולא יישמרו ב-Cache
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = df.fillna("")
    except:
        st.error("שגיאה בחיבור לגיליון. וודא שקיים גיליון בשם Sheet1 עם הכותרות המתאימות.")
        st.stop()

    st.title("🎫 ארנק הקופונים שלי")

    # --- תפריט צדדי ---
    st.sidebar.header("⚙️ תפריט")
    menu = st.sidebar.radio("פעולה:", ["צפייה בקופונים", "הוספה ידנית", "טעינה מאקסל"])

    if menu == "הוספה ידנית":
        st.subheader("➕ הוספת קופון חדש")
        with st.form("add_form"):
            col1, col2 = st.columns(2)
            with col1:
                store = st.text_input("שם הרשת")
                val = st.text_input("סכום / מוצר")
                c_type = st.selectbox("סוג:", ["קוד/מספר", "לינק", "כרטיס עם CVV"])
            with col2:
                code = st.text_input("הקוד או הלינק המלא")
                expiry = st.text_input("תוקף")
                cvv = st.text_input("CVV (אם יש)")
            
            notes = st.text_area("הערות")
            
            if st.form_submit_button("שמור לענן"):
                new_data = pd.DataFrame([{"רשת": store, "סוג": c_type, "סכום_או_מוצר": val, 
                                          "קוד_או_לינק": code, "תוקף": expiry, "CVV": cvv, "הערות": notes}])
                updated_df = pd.concat([df, new_data], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("נשמר בהצלחה!")
                st.rerun()

    elif menu == "טעינה מאקסל":
        st.subheader("📥 ייבוא מאקסל")
        file = st.file_uploader("בחר קובץ", type=['xlsx', 'csv'])
        if file:
            new_df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file)
            if st.button("אשר העלאה לענן"):
                updated_df = pd.concat([df, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("הנתונים עלו לגיליון!")
                st.rerun()

    else: # צפייה בקופונים
        search = st.text_input("🔍 חפש רשת (למשל: רמי לוי, Dream Card):")
        filtered_df = df[df['רשת'].str.contains(search, case=False, na=False)] if search else df

        if filtered_df.empty:
            st.info("אין קופונים להצגה.")
        else:
            for i, row in filtered_df.iterrows():
                # עיצוב הכרטיסייה
                with st.expander(f"**{row['רשת']}** | {row['סכום_או_מוצר']}"):
                    col_info, col_action = st.columns([2, 1])
                    
                    with col_info:
                        st.write(f"**תוקף:** {row['תוקף']}")
                        if row['CVV']:
                            st.write(f"**CVV:** {row['CVV']}")
                        if row['הערות']:
                            st.info(f"הערות: {row['הערות']}")

                    with col_action:
                        # בדיקה אם מדובר בלינק או בקוד
                        raw_code = str(row['קוד_או_לינק']).strip()
                        if raw_code.startswith("http"):
                            st.link_button("פתח לינק מלא 🔗", raw_code)
                            st.caption(raw_code) # מציג את הלינק מתחת לכפתור
                        else:
                            st.subheader("הקוד:")
                            st.code(raw_code, language="text")
                            st.caption("לחץ להעתקת המספר")

                    # כפתור מחיקה קטן בתחתית כל קופון
                    if st.button(f"מחק קופון זה", key=f"del_{i}"):
                        updated_df = df.drop(i).reset_index(drop=True)
                        conn.update(worksheet="Sheet1", data=updated_df)
                        st.rerun()

    if st.sidebar.button("התנתק"):
        st.session_state.authenticated = False
        st.rerun()
