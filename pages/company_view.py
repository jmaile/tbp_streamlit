import numpy as np
import pandas as pd
import streamlit as st

from faker import Faker
st.set_page_config(page_title="Company View", layout="wide")

conn = st.connection("snowflake")

@st.cache_data
def get_open_tickets_df():

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

open_tickets = get_open_tickets_df()

with st.container(border=True):

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
            filtered_df = open_tickets_filtered_by_company[open_tickets_filtered_by_company['company'] == tab_name]
            selected_ihd_month = st.selectbox(f"Select a product for {tab_name}",
                                            filtered_df['ihd_month'].drop_duplicates().tolist())
            if selected_ihd_month:
                filtered_df = filtered_df[filtered_df['ihd_month'] == selected_ihd_month]


            st.text(f'{len(filtered_df)} Open Orders Found')

            # Display dataframe and allow row selection
            selected_row_index = st.dataframe(
                filtered_df.sort_values(by=['ship_date', 'ihd'], ascending=[True, True]),
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
                selected_order = filtered_df.iloc[_order].to_dict('records')[0]
                st.write(selected_order)
            else:
                st.write('Select an Order')