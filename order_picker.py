import random

import streamlit as st
import pandas as pd
import pydeck as pdk

st.set_page_config(page_title="Order Picker", layout="wide")


conn = st.connection("snowflake")


@st.cache_data
def load_data_from_db():
    return pd.read_sql(sql='select * from TASTY_BYTES_SAMPLE_DATA.RAW_POS.COMPANY', con=conn)


df = load_data_from_db()

df['ticket_description'] = (
    df['ticket_id'].astype(str) + ' | ' +
    df['company'] + ' | ' +
    pd.to_datetime(df['ship_date']).dt.strftime('%Y-%m-%d') + ' | ' +  # Format ship_date
    df['ihd'] + '|  ' +
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

page_col1, page_col2 = st.columns(2)

with page_col1:

    # Create a container for the ticket input and details\
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center;'>Ticket Details</h2>", unsafe_allow_html=True)

        # Selectbox for choosing a ticket description
        selected_ticket_description = st.selectbox(
            "Select a Ticket ID",
            set(df['ticket_description'].tolist()),
            help="Choose a ticket to view its details"
        )

        # Display ticket details inside a professional container
        with st.container():
            # Display the fields in a neat way with labels
            st.markdown(f"<h4 style='text-align: center;'>Ticket Information for {get_field_for_selected_ticket(selected_ticket_description, 'ticket_id')} </h4>", unsafe_allow_html=True)

            col1, col2, col3 = st.columns(3)
            with col1:
                ticket_info = []
                st.markdown(f'[AdOrbit](https://tbp.adorbit.com/tickets/ticket/?id={get_field_for_selected_ticket(selected_ticket_description, "ticket_id")})')

                for x in ['rep']:
                    ticket_info.append(x.upper().replace('_', ' ') + ' : ' + get_field_for_selected_ticket(selected_ticket_description, x))
                st.write('<br>'.join(ticket_info), unsafe_allow_html=True)

            with col2:
                ticket_info = []
                for x in [ 'status', 'data_file_status']:
                    ticket_info.append(x.upper().replace('_', ' ') + ' : ' + get_field_for_selected_ticket(selected_ticket_description, x))
                st.write('<br>'.join(ticket_info), unsafe_allow_html=True)

            with col3:
                ticket_info = []
                for x in ['ship_date', 'ihd']:
                    ticket_info.append(x.upper().replace('_', ' ') + ' : ' + get_field_for_selected_ticket(selected_ticket_description, x))
                st.write('<br>'.join(ticket_info), unsafe_allow_html=True)

            st.write(get_field_for_selected_ticket(selected_ticket_description, 'original_ticket_summary'))

            st.divider()

            # Initialize session state for keeping track of the number of file selectors
            if 'file_count' not in st.session_state:
                st.session_state.file_count = 1  # Start with 1 file selectbox

            # Layout columns
            col1, col2 = st.columns(2)

            # Track the selected files and options for each file
            file_selects = []
            file_options = []

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
                        f"Choose an option for File {i + 1}",
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


            st.divider()

            # Button to add new record
            if st.button("Add to Count"):
                add_record()
                st.success("New order added to count!")

with page_col2:
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center;'>Map</h2>", unsafe_allow_html=True)
        mapping_df = pd.read_pickle(
            r"\\192.168.4.16\Mail Files\Mailing Lists\TBPDB_Automation\tbpdb_lists\tbpdb_cass_out\01Mar25-250301_TTNZ_MLRSRS_C-CASS250302.pkl"
        )
        mapping_df = mapping_df.dropna()


        def generate_random_color():
            hex_color = f"#{random.randint(0, 0xFFFFFF):06x}"  # Generate hex color
            # Convert hex color to RGBA format
            hex_color = hex_color.lstrip('#')
            return str([random.randint(0, 255) for _ in range(4)])

        # Map random colors to each unique 'BCC_CASS_SCF' label
        unique_labels = mapping_df['BCC_CASS_SCF Label'].unique()
        label_to_color = {label: generate_random_color() for label in unique_labels}
        # Add a new column 'random_color' based on the mapping
        mapping_df['scf_color'] = mapping_df['BCC_CASS_SCF Label'].map(label_to_color)


        mapping_df['mapping_zip'] = mapping_df['BCC_CASS_zip'].astype(str).str[:7]
        mapping_df['BCC_CASS_Latitude'] = pd.to_numeric(mapping_df['BCC_CASS_Latitude'],errors='coerce')
        mapping_df['BCC_CASS_Longitude'] = pd.to_numeric(mapping_df['BCC_CASS_Longitude'],errors='coerce')
        # Group by 'zip' and calculate mean and count for latitude and longitude
        grouped_df = mapping_df.dropna(subset=['BCC_CASS_Latitude', 'BCC_CASS_Longitude']).groupby(['scf_color','mapping_zip']).agg(
            mean_lat=('BCC_CASS_Latitude', 'mean'),  # Mean of latitude
            mean_long=('BCC_CASS_Longitude', 'mean'),  # Mean of longitude
            count_lat=('BCC_CASS_Latitude', 'size'),  # Count of non-null latitudes
        ).reset_index()


        column_layer =  pdk.Layer(
            'HexagonLayer',
            data=mapping_df,
            get_position='[BCC_CASS_Longitude, BCC_CASS_Latitude]',
            #get_elevation="count_lat",
            auto_highlight=True,
            elevation_scale=50,

            pickable=True,
            elevation_range=[0, 500],
            extruded=True,
            coverage=1
        )

        tooltip = {
            "html": "<b>{count_lat}</b> meters away from an MRT station, costs <b>{price_per_unit_area}</b> NTD/sqm",
            "style": {"background": "grey", "color": "white", "font-family": '"Helvetica Neue", Arial',
                      "z-index": "10000"},
        }


        r = pdk.Deck(
            column_layer,
            initial_view_state=pdk.ViewState(
                latitude=grouped_df['mean_lat'].mean(),  # Set the center of the map
                longitude=grouped_df['mean_long'].mean(),
                zoom=10,

                pitch=50
            ),
            map_provider='mapbox',
            map_style='mapbox://styles/mapbox/light-v10',  # Set the map style to 'light'
            tooltip=tooltip
        )

        # Display the map with Pydeck chart in Streamlit
        st.pydeck_chart(r)

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

with st.container(border=True):
    st.markdown("<h2 style='text-align: center;'>Count</h2>", unsafe_allow_html=True)

    # Display grouped data with collapsible sections
    st.write("Ticket Data (Grouped by Company)")

    # Iterate over the groups
    for company, group in grouped:
        with st.expander(f"(5 M/ 2 S) 12345 | syunner | ds"):
            # Display the group inside the expander
            st.dataframe(group)



    # Button to add new record
    if st.button(f"Send Count to {get_field_for_selected_ticket(selected_ticket_description, 'rep')}"):
        st.success("New order added to count!")