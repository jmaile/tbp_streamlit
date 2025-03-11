import streamlit as st


# Simulated function to suggest a company
def suggest_company(record):
    # Placeholder for a function that takes some time to compute
    return f"Suggested Company for {record}"


# Sample data of records (e.g., IDs, names, etc.)
records = [f"Record {i}" for i in range(1, 101)]  # 100+ records

# Pre-selected list of companies
companies = ["Company A", "Company B", "Company C", "Company D", "Company E"]


# Function to display the records and allow company assignment
def display_batch(start_index):
    batch = records[start_index:start_index + 5]  # Show 5 records at a time
    assigned_companies = {}

    for i, record in enumerate(batch):
        # Show the suggested company
        suggested = suggest_company(record)
        st.write(f"**{record}**")
        st.write(f"Suggested: {suggested}")

        # Dropdown to select a company
        selected_company = st.selectbox(f"Assign company to {record}", companies, key=f"{record}_selectbox")
        assigned_companies[record] = selected_company

    return assigned_companies


# Streamlit sidebar to navigate between batches
batch_size = 5
total_batches = len(records) // batch_size

# Session state to keep track of the current batch
if 'batch_index' not in st.session_state:
    st.session_state.batch_index = 0

# Show the current batch of records
assigned_companies = display_batch(st.session_state.batch_index * batch_size)

# Buttons for navigation
col1, col2 = st.columns(2)

with col1:
    if st.session_state.batch_index > 0:
        if st.button("Previous Batch"):
            st.session_state.batch_index -= 1

with col2:
    if st.session_state.batch_index < total_batches - 1:
        if st.button("Next Batch"):
            st.session_state.batch_index += 1

# Display the assigned companies (Optional)
st.write("Assignments for the current batch:")
st.write(assigned_companies)

