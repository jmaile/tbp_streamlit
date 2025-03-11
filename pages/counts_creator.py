import random

import pandas as pd
import streamlit as st
import json
import pydeck as pdk

import scripts

st.set_page_config(page_title="Counts Curator", layout="wide",  initial_sidebar_state='collapsed')
st.write("http://localhost:8501/counts_creator?ticket_id=118110")

# todo stay on tab when reload
@st.dialog("Process Counts", width='large')
def open_process_counts_dialog(mapping_df):
    with st.container(border=True):
        st.markdown("<h2 style='text-align: center;'>Map</h2>", unsafe_allow_html=True)

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
        mapping_df['BCC_CASS_Latitude'] = pd.to_numeric(mapping_df['BCC_CASS_Latitude'], errors='coerce')
        mapping_df['BCC_CASS_Longitude'] = pd.to_numeric(mapping_df['BCC_CASS_Longitude'], errors='coerce')
        # Group by 'zip' and calculate mean and count for latitude and longitude
        grouped_df = mapping_df.dropna(subset=['BCC_CASS_Latitude', 'BCC_CASS_Longitude']).groupby(
            ['scf_color', 'mapping_zip']).agg(
            mean_lat=('BCC_CASS_Latitude', 'mean'),  # Mean of latitude
            mean_long=('BCC_CASS_Longitude', 'mean'),  # Mean of longitude
            count_lat=('BCC_CASS_Latitude', 'size'),  # Count of non-null latitudes
        ).reset_index()
        column_layer = pdk.Layer(
            'HexagonLayer',
            data=mapping_df,
            get_position='[BCC_CASS_Longitude, BCC_CASS_Latitude]',
            # get_elevation="count_lat",
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



def load_snowflake_tables():
    conn = st.connection("snowflake")

    files_assigned = pd.read_sql(
        sql=
        """
            select * from TBP.FILE_DROP.CASSED_FILENAMES where "assigned_company_id" is not null
        """
        ,
        con=conn
    )

    companies = pd.read_sql(
        sql=
        """
            select * from TASTY_BYTES_SAMPLE_DATA.RAW_POS.COMPANY
        """
        ,
        con=conn
    )

    return {
        'files_assigned': files_assigned,
        'companies': companies
    }


snowflake_tables = load_snowflake_tables()
open_tickets = scripts.snowflake_data.get_cached_data('open_tickets').sort_values(by='ihd', ascending=True)
all_companies = scripts.snowflake_data.get_cached_data('companies')

files_assigned = snowflake_tables['files_assigned']
# ----- Check Ticket ID in URL ------------------------------------------------------------

URL_TICKET = None
query_params = st.query_params
if 'ticket_id' in query_params:
    URL_TICKET = int(query_params['ticket_id'])
    if URL_TICKET not in open_tickets['ticket_id'].tolist():
        st.warning(f'Ticket {URL_TICKET} is invalid!')
        URL_TICKET = None
    else:
        st.success(f"Parsed ticket ID from URL: {URL_TICKET}")
else:
    st.write("No ticket_id found in the URL.")

# ------------------------------------------------------------

with st.container(border=True):
    selected_order = False
    st.markdown("<h2 style='text-align: center;'>Add Ticket to Counts Cart</h2>", unsafe_allow_html=True)

    default_company = None
    if URL_TICKET:
        default_company = open_tickets[open_tickets['ticket_id'] == URL_TICKET]['company'].tolist()[0]

    companies = st.multiselect(
        "Add a company",
        all_companies['company_name'].tolist(),
        default=default_company
    )

    # filter open tickets for that company
    open_tickets = open_tickets[open_tickets['company'].isin(companies)]

    if companies:
        tabs = st.tabs(companies)
        if 'selected_tab' not in st.session_state:
            st.session_state.selected_tab = companies[0] # Default tab
        for tab_name, tab in zip(companies, tabs):
            with tab:
                tab_df = open_tickets[open_tickets['company'] == tab_name]
                default_index = 0
                default_product = 'Solo Mailers'
                if URL_TICKET and tab_name == default_company:
                    default_index = None
                    default_product = open_tickets[open_tickets['ticket_id'] == URL_TICKET]['product'].tolist()[0]

                col1, col2 = st.columns([1,12])
                with col1:
                    checkbox_values = {}
                    for product in tab_df['product'].drop_duplicates().tolist():
                        checkbox_values[product] = st.checkbox(product, value=(product == default_product),  key=str(tab_name) + str(product))

                    # Display the selected checkboxes
                    selected_products = [product for product in tab_df['product'].drop_duplicates().tolist() if checkbox_values[product]]
                    tab_df = tab_df[tab_df['product'].isin(selected_products)]

                with col2:
                    # Define function to color rows
                    def color_rows(row):
                        color = [''] * len(row)  # Initialize with no color (empty string) for all columns

                        # Apply color to all columns if flip == 1
                        if row.get('flip') == 1:
                            color = ['background-color: lightgrey; color: black'] * len(row)  # Color all columns when flip == 1

                        if row['ticket_id'] == URL_TICKET:
                            color[tab_df.columns.get_loc('ticket_id')] = 'background-color: #f2eda7; color: black'  # Highlight the ticket_id cell

                        return color
                    display_cols = ['rep', 'company_id', 'company', 'product', 'tbpdb_campaign', 'ticket_id', 'ticket_summary', 'adorbit_qty', 'ship_date', 'ihd', 'tbpdb_status', 'data_file_status', 'status', 'ihd_month']
                    tab_df = tab_df.sort_values(by=['product', 'raw_ihd', 'ship_date'],ascending=[True, True, True])[display_cols]

                    tab_df['flip'] = tab_df['ihd_month'].ne(tab_df['ihd_month'].shift()).cumsum() % 2

                    tab_df_styled = tab_df.style.apply(color_rows, axis=1)

                    ncol1, ncol2 = st.columns(2)
                    with ncol1:
                        with st.expander("Data Requests"):
                            st.write('''
                            you got this justice
    
                            ''')

                    with ncol2:
                        with st.expander("View Closed Tickets"):
                            st.write('''
                            you got this justice
    
                            ''')

                selected_row_index = st.dataframe(
                    tab_df_styled,
                    use_container_width=True,
                    hide_index=True,
                    on_select="rerun",
                    selection_mode="multi-row",
                    key=tab_name
                )
                selected_tickets = selected_row_index.selection.rows
                if 'cart_df' not in st.session_state:
                    st.session_state.cart_df = pd.DataFrame(
                        columns=tab_df.columns)  # Initialize an empty cart DataFrame

                if selected_tickets:
                    _to_add = tab_df.iloc[selected_tickets]
                    _to_add = _to_add[~(_to_add['ticket_id'].isin(st.session_state.cart_df['ticket_id']))]
                    if st.button(f"Add {len(selected_tickets)} Tickets to Cart", key=tab_name + 'add_to_cart'):
                        st.session_state.cart_df = pd.concat(
                            [
                                st.session_state.cart_df,
                                _to_add
                            ],
                            ignore_index=True
                        )

                else:
                    st.warning('Select a Ticket')



with st.container(border=True):
    selected_order = False
    if 'cart_df' not in st.session_state:
        None
    elif len(st.session_state.cart_df) == 0:
        st.session_state.cart_df['mail_files'] = 0
        st.session_state.cart_df['scrub_files'] = 0
    else:
        st.markdown("<h2 style='text-align: center;'>Counts Cart</h2>", unsafe_allow_html=True)
        unique_ihd_months = st.session_state.cart_df['ihd_month'].drop_duplicates().tolist()
        if len(unique_ihd_months) > 1:
            st.warning(f'Multiple IHD Months Found: ' + ' | '.join(unique_ihd_months))
        for ticket_info, _df in st.session_state.cart_df.groupby(['company', 'ihd_month', 'ticket_id', 'company_id']):
            company_id=ticket_info[-1]
            with st.expander(f"{' | '.join([str(x) for x in list(ticket_info)])}", expanded=True):
                col1, col2 = st.columns([3, 3])
                with col1:
                    st.json(
                        _df.to_dict('records')[0],
                        expanded=False
                    )

                    if "lists_on_hand" in st.session_state or "po_list" in st.session_state:
                        if "lists_on_hand" in st.session_state:
                            st.write('Lists on Hand')

                            st.write( st.session_state.lists_on_hand)

                        if "po_list" in st.session_state:
                            st.write('Purchased Lists:')
                            st.write(st.session_state.po_list)

                        if st.button('Process Count'):
                            bcc_cass_dfs = pd.DataFrame()
                            # http://localhost:8501/counts_creator?ticket_id=117852
                            selected_files_assigned = files_assigned[files_assigned['original_filename'].isin(list(st.session_state.lists_on_hand.keys()))]
                            for selected_file_dict in selected_files_assigned.to_dict('records'):
                                desigantion = st.session_state.lists_on_hand[selected_file_dict['original_filename']]
                                snowflake_filename = selected_file_dict['snowflake_filename']
                                debug = True
                                if debug:
                                    sf_df = pd.read_parquet('snowflake_staging_snapshot.pqt')
                                else:
                                    sf_df = scripts.snowflake_data.get_staging_parquet_file_as_df(snowflake_filename)

                                sf_df = sf_df[[x for x in sf_df.columns if 'BCC_CASS' in x]]
                                sf_df['designation'] = desigantion
                                bcc_cass_dfs = pd.concat([sf_df, bcc_cass_dfs])
                                st.write(desigantion + snowflake_filename)
                            # give it the purchosed lists, and type -> df
                            open_process_counts_dialog(bcc_cass_dfs)


                with col2:
                    st.markdown("<h3 style='text-align: center;'>Add Files</h3>", unsafe_allow_html=True)

                    options = st.multiselect(
                        "Filter for Companies",
                        all_companies['company_name'].tolist(),
                        tab_name,
                        key=f"companies_for_{ticket_info}"  # Unique key for each selectbox
                    )


                    with st.form(tab_name + 'lists_on_hand'):

                        # Initialize session state for the PO list if it doesn't exist
                        if "lists_on_hand" not in st.session_state:
                            st.session_state.lists_on_hand = {}


                        selected_file_col, file_assignment_col = st.columns([10, 2])
                        with selected_file_col:
                            files_assigned['priority'] = 0
                            files_assigned.loc[ (files_assigned['assigned_company_id'].astype(int) == int(company_id) ), 'priority'] = 1

                            _files = [x['original_filename']for x in files_assigned.sort_values(by=['priority', 'file_creation_date'], ascending=[False, False]).to_dict('records')]

                            selected_file = st.selectbox(
                                f"Select File",
                                _files,
                                key=f"file_for_{ticket_info}"  # Unique key for each selectbox
                            )

                        with file_assignment_col:
                            scrub_or_mail = st.radio(
                                f"File Designation",
                                options=["Scrub", "Mail"],
                                index=1,  # Default option
                                key=f"option_for_{ticket_info}"  # Unique key for each selectbox
                            )

                        if st.form_submit_button('Add a File on Hand'):
                            if selected_file and selected_file:  # Ensure that the text input isn't empty

                                st.session_state.lists_on_hand[selected_file] = scrub_or_mail
                                # Clear the input field after adding
                                st.rerun()

                    # ----- Purchase Orders (MH,etc)
                    with st.form(tab_name + 'purchased_lists'):

                        # Initialize session state for the PO list if it doesn't exist
                        if "po_list" not in st.session_state:
                            st.session_state.po_list = []

                        # Input for Purchase Order #
                        title = st.text_input("Purchased Order #", None, placeholder='MH #T00000000')

                        # Button to add the PO to the list
                        if st.form_submit_button('Add a Purchased List'):
                            if title and title not in st.session_state.po_list:  # Ensure that the text input isn't empty
                                st.session_state.po_list.append(title)
                                # Clear the input field after adding
                                st.rerun()

                    # ---------------------------------------------------------------------------------------------------------

        if st.button("Clear Cart"):
            st.session_state.cart_df = st.session_state.cart_df.head(0)
            st.rerun()

