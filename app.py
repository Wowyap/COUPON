import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import re

# --- Security Settings ---
PASSWORD = "1"

st.set_page_config(page_title="My Coupon Wallet", layout="wide", page_icon="🎫")

def check_password():
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if not st.session_state.authenticated:
        st.title("🔒 Login")
        pwd = st.text_input("Password:", type="password")
        if st.button("Enter"):
            if pwd == PASSWORD:
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Wrong password")
        return False
    return True

# Helper to sum amounts for the dashboard summary
def parse_amount(val):
    try:
        val = str(val).lower().replace('₪', '').strip()
        if 'x' in val:
            parts = val.split('x')
            return float(parts[0]) * float(parts[1])
        numbers = re.findall(r"[-+]?\d*\.\d+|\d+", val)
        return float(numbers[0]) if numbers else 0.0
    except:
        return 0.0

if check_password():
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    try:
        # Read with ttl=0 to ensure real-time updates from Google Sheets
        df = conn.read(worksheet="Sheet1", ttl="0")
        df = df.fillna("")
    except Exception as e:
        st.error(f"Connection Error: {e}")
        st.stop()

    st.title("🎫 My Coupon Wallet")

    # --- Dashboard Summary Section ---
    if not df.empty:
        total_value = df['value'].apply(parse_amount).sum()
        col1, col2 = st.columns(2)
        col1.metric("Total Estimated Value", f"{total_value:,.2f} ₪")
        col2.metric("Total Active Coupons", len(df))
        st.markdown("---")

    # --- Sidebar Management ---
    st.sidebar.header("Navigation")
    action = st.sidebar.radio("Go to:", ["My Wallet", "Add Manually", "Bulk Upload"])

    if action == "Add Manually":
        st.subheader("➕ Add New Coupon")
        with st.form("add_form"):
            net = st.text_input("Network (e.g., Rami Levy)")
            v = st.text_input("Value (e.g., 50 or 50x5)")
            t = st.selectbox("Type", ["Link", "Code", "Credit Card"])
            code = st.text_input("Code or URL")
            exp = st.text_input("Expiry (DD-MM-YYYY)")
            cvv = st.text_input("CVV")
            n = st.text_area("Notes")
            if st.form_submit_button("Save to Sheets"):
                new_row = pd.DataFrame([{"network": net, "type": t, "value": v, 
                                          "code_or_link": code, "expiry": exp, "cvv": cvv, "notes": n}])
                updated_df = pd.concat([df, new_row], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Saved successfully!")
                st.rerun()

    elif action == "Bulk Upload":
        st.subheader("📥 Bulk Upload")
        file = st.file_uploader("Upload CSV/Excel", type=['xlsx', 'csv'])
        if file:
            new_df = pd.read_excel(file) if file.name.endswith('xlsx') else pd.read_csv(file, encoding='utf-8-sig')
            if st.button("Merge and Upload"):
                updated_df = pd.concat([df, new_df], ignore_index=True)
                conn.update(worksheet="Sheet1", data=updated_df)
                st.success("Bulk update complete!")
                st.rerun()

    else: # My Wallet (Hierarchical View)
        search = st.text_input("🔍 Filter by network:")
        display_df = df[df['network'].str.contains(search, case=False, na=False)] if search else df

        if display_df.empty:
            st.info("No records found.")
        else:
            # Grouping items by network name for cleaner UI
            networks = sorted(display_df['network'].unique())
            
            for net in networks:
                net_coupons = display_df[display_df['network'] == net]
                with st.expander(f"➕ {net} ({len(net_coupons)} coupons)"):
                    for i, row in net_coupons.iterrows():
                        c1, c2, c3, c4 = st.columns([1, 2.5, 1, 0.5])
                        
                        with c1:
                            st.write(f"**{row['value']}**")
                            if row['expiry']: st.caption(f"Expires: {row['expiry']}")
                        
                        with c2:
                            val = str(row['code_or_link']).strip()
                            if val.startswith("http"):
                                # Display button AND raw text link
                                st.link_button("Open Link 🔗", val)
                                st.caption(f"Full URL: {val}")
                            else:
                                st.code(val, language="text")
                        
                        with c3:
                            if row['cvv']: st.write(f"CVV: {row['cvv']}")
                            if row['notes']: st.info(row['notes'])
                            
                        with c4:
                            # Unique key for each delete button based on index
                            if st.button("🗑️", key=f"del_{i}"):
                                full_df = conn.read(worksheet="Sheet1", ttl="0")
                                full_df = full_df.drop(i).reset_index(drop=True)
                                conn.update(worksheet="Sheet1", data=full_df)
                                st.rerun()
                        st.markdown("---")

    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()
