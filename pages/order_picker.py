import random

import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Order Picker", layout="wide",  initial_sidebar_state='collapsed')

conn = st.connection("snowflake")

st.write('<style>body {  margin: 0;  font-family: Arial, Helvetica, sans-serif;} .header{padding: 10px 16px;  background: #555;  color: #f1f1f1; position:fixed;top:0;} .sticky {  position: fixed; top: 90;  width: 100%;}  </style><div class="header" id="myHeader">'+'dsdad'+'</div>', unsafe_allow_html=True)

@st.cache_data
def load_data_from_db():

    df = pd.read_sql(
        sql=
            """
                select * from TASTY_BYTES_SAMPLE_DATA.RAW_POS.OPEN_TICKETS
            """
        ,
        con=conn
    )

    df = df[
        [
            'rep',
            'ticket_id',
            'company',
            'product',
            'product_size',
            'data_file_status',
            'status',
            'tbpdb_status',
            'ship_date',
            'ihd',
            'adorbit_qty',
            'tbpdb_campaign',
            'ticket_summary',
        ]
    ]
    df['ihd'] = pd.to_datetime(df['ihd'])
    df['ihd_month'] = df['product'] + ' for ' + df['ihd'].apply(lambda x: x.replace(day=1).strftime('%B, %Y'))
    return df

df = load_data_from_db()


open_tickets = df.copy()



df['ticket_description'] = (
    df['ticket_id'].astype(str) + ' | ' +
    df['company'] + ' | ' +
    pd.to_datetime(df['ship_date']).dt.strftime('%Y-%m-%d') + ' | ' +  # Format ship_date
    df['ihd'].dt.strftime('%Y-%m-%d') + '|  ' +
    df['status'] + ' (' + df['data_file_status'] + ')'  # Include data_file_status
)

def get_field_for_selected_ticket(ticket_description, field):
    if field not in df.columns:
        return f'"{field}" not present in df.'
    return str(df.fillna('-').loc[df['ticket_description'] == ticket_description, field].squeeze())


# Initialize session state to store the table if not already initialized
if 'data' not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=["Name", "Age", "City"])

# Function to add a new record to the table
def add_record():
    new_data = {
        "Name": st.session_state.new_name,
        "Age": st.session_state.new_age,
        "City": st.session_state.new_city
    }
    new_row = pd.DataFrame([new_data])  # Create a new DataFrame for the new row
    st.session_state.data = pd.concat([st.session_state.data, new_row], ignore_index=True)  # Use pd.concat instead of append


selected_ticket_description = None

# Create a container for the ticket input and details\
with st.container(border=True):
    selected_order = False
    st.markdown("<h2 style='text-align: center;'>Select an Order</h2>", unsafe_allow_html=True)

    with st.container(border=True):

        col1, col2 = st.columns([4, 3])
        with col1:
            companies = st.multiselect(
                "Add a company",
                open_tickets['company'].drop_duplicates().tolist()
            )

            open_tickets_filtered_by_company = open_tickets[open_tickets['company'].isin(companies)]
            # Create tabs for each company
            tabs = st.tabs(companies)

            # Loop through each tab and display the respective dataframe
            for tab_name, tab in zip(companies, tabs):
                with tab:

                    # Filter the dataframe based on the company for the current tab
                    filtered_df = open_tickets_filtered_by_company[
                        open_tickets_filtered_by_company['company'] == tab_name]
                    selected_ihd_month = st.selectbox(f"Select a product for {tab_name}",
                                                      filtered_df['ihd_month'].drop_duplicates().tolist())
                    if selected_ihd_month:
                        filtered_df = filtered_df[filtered_df['ihd_month'] == selected_ihd_month]

                    st.text(f'{len(filtered_df)} Open Orders Found')
                    filtered_df = filtered_df.sort_values(by=['ship_date', 'ihd'], ascending=[True, True])
                    # Display dataframe and allow row selection
                    selected_row_index = st.dataframe(
                        filtered_df,
                        use_container_width=True,
                        hide_index=True,
                        on_select="rerun",
                        selection_mode="single-row",
                    )

                    with st.expander("Closed Orders"):
                        st.write('''
                            sutm cute                    
                        ''')
                    _order = selected_row_index.selection.rows
                    if _order:
                        selected_order = filtered_df.to_dict('records')[_order[0]]

        with col2:

            if selected_order:
                # Display the fields in a neat way with labels
                st.markdown(f"<h4 style='text-align: center;'>Ticket Information for {selected_order['ticket_id']} </h4>", unsafe_allow_html=True)
                st.write(selected_order)
            else:
                'Select an Order!!!'
    # Display ticket details inside a professional container
    if selected_order:
        with st.container():
            st.markdown("<h2 style='text-align: center;'>Add File(s)</h2>", unsafe_allow_html=True)

            # Initialize session state for keeping track of the number of file selectors
            if 'file_count' not in st.session_state:
                st.session_state.file_count = 1  # Start with 1 file selectbox

            # Layout columns

            # Track the selected files and options for each file
            file_selects = []
            file_options = []
            p_col1, p_col2 = st.columns(2)

            with p_col1:
                col1, col2 = st.columns([10,2])
                # Generate selectboxes and radio buttons dynamically based on the file count
                for i in range(st.session_state.file_count):

                    with col1:
                        # Use session state to store the selection for each file
                        selected_file = st.selectbox(
                            f"Select File {i + 1}",
                            ('file-id...', 'another-file-id...', 'file-xyz...'),
                            key=f"file_{i}"  # Unique key for each selectbox
                        )
                        file_selects.append(selected_file)  # Store the selection

                    with col2:
                        # Radio button to choose an option for each file
                        selected_option = st.radio(
                            f"File Designation",
                            options=["Scrub", "Mail"],
                            index=1,  # Default option
                            key=f"option_{i}"  # Unique key for each radio button
                        )
                        file_options.append(selected_option)  # Store the selection

                # Button to add another file selectbox
                if st.button("Add a File"):
                    # Increment the file count in session state when button is clicked
                    st.session_state.file_count += 1
                    st.rerun()

            with p_col2:
                st.write('map')

            # Button to add new record
            if st.button("Add to Count"):
                add_record()
                st.success("New order added to count!")

            st.divider()

            # Sample DataFrame
            test_df = {
                'ticket_id': [1, 2, 3, 4, 5, 6],
                'company': ['Company A', 'Company A', 'Company B', 'Company B', 'Company A', 'Company B'],
                'ship_date': ['2025-03-01', '2025-03-02', '2025-03-01', '2025-03-03', '2025-03-02', '2025-03-04'],
                'status': ['Open', 'Closed', 'Open', 'Closed', 'Open', 'Closed']
            }

            # Create DataFrame
            test_df = pd.DataFrame(test_df)

            # Group the DataFrame by 'company'
            grouped = test_df.groupby('company')

            st.markdown("<h2 style='text-align: center;'>Count Sign-Off</h2>", unsafe_allow_html=True)

            # Button to add new record
            if st.button(f"Email Count to {get_field_for_selected_ticket(selected_ticket_description, 'rep')}"):
                st.success("New order added to count!")