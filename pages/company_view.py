import streamlit as st
import pandas as pd

# Sample data for tables (same as before)
table1 = pd.DataFrame({'Col1': [1, 2, 3], 'Col2': ['A', 'B', 'C']})
table2 = pd.DataFrame({'Col1': [4, 5, 6], 'Col2': ['D', 'E', 'F']})

# Notification data (name and count of issues)
notifications = {
    "Warning 1: Data Inconsistency": 5,
    "Warning 2: Missing Values": 3,
    "Warning 3: System Error": 2,
}

# Main section for notifications
st.header("Notifications")
for notification, count in notifications.items():
    with st.expander(f"{notification} ({count})"):
        if st.button(f"View details for {notification}"):
            st.session_state.selected_notification = notification

# Display the table based on the selected notification
if 'selected_notification' in st.session_state:
    selected_notification = st.session_state.selected_notification
    st.write(f"You selected: {selected_notification}")

    if selected_notification == "Warning 1: Data Inconsistency":
        st.write(table1)
    elif selected_notification == "Warning 2: Missing Values":
        st.write(table2)
    elif selected_notification == "Warning 3: System Error":
        # Placeholder for actual error data
        st.write("Here are the details for System Errors...")
        st.write(table1)  # Placeholder
else:
    st.write("Please select a notification to view details.")
