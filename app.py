else: # My Wallet (תצוגת הקופונים)
        search = st.text_input("🔍 חיפוש רשת...", placeholder="הקלד שם רשת לסינון")
        
        # סינון ה-DF לפי החיפוש
        if search:
            display_df = df[df['network'].str.contains(search, case=False, na=False)]
        else:
            display_df = df

        if display_df.empty:
            st.info("לא נמצאו קופונים התואמים לחיפוש.")
        else:
            # חילוץ רשימת הרשתות הייחודיות מתוך הנתונים המסוננים
            networks = sorted(display_df['network'].unique())
            
            for net in networks:
                # כאן אנחנו מגדירים את net_coupons עבור כל רשת בנפרד
                net_coupons = display_df[display_df['network'] == net]
                
                with st.expander(f"🏢 {net.upper()} — ({len(net_coupons)} פריטים)"):
                    # עכשיו הלולאה הזו תעבוד כי היא בתוך הטווח שבו net_coupons קיים
                    for i, row in net_coupons.iterrows():
                        with st.container(border=True):
                            c1, c2, c3 = st.columns([1, 2, 0.6])
                            
                            with c1:
                                st.markdown(f"### {row['value']} ₪")
                                if row['expiry']: st.caption(f"📅 תוקף: {row['expiry']}")
                                if row['cvv']: st.markdown(f"**CVV:** `{row['cvv']}`")
                            
                            with c2:
                                val = str(row['code_or_link']).strip()
                                if val.startswith("http"):
                                    st.link_button("🌐 פתח קישור", val, use_container_width=True)
                                else:
                                    st.code(val, language="text")
                                if row['notes']: st.caption(f"📝 {row['notes']}")
                            
                            with c3:
                                # כפתור עריכה - קורא לדיאלוג שהגדרנו למעלה
                                if st.button("✏️", key=f"edit_{i}", help="ערוך קופון", use_container_width=True):
                                    edit_coupon_dialog(i, row, df, conn)
                                
                                # כפתור מחיקה
                                if st.button("🗑️", key=f"del_{i}", help="מחק קופון", use_container_width=True):
                                    # קריאה מחדש של הנתונים כדי למנוע מחיקת שורה לא נכונה
                                    full_df = conn.read(worksheet="Sheet1", ttl="0")
                                    full_df = full_df.drop(i).reset_index(drop=True)
                                    conn.update(worksheet="Sheet1", data=full_df)
                                    st.success("הקופון נמחק")
                                    st.rerun()
