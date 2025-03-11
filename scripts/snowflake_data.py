# snowflake_data.py
import json
from datetime import datetime

import numpy as np
import snowflake.connector
import pandas as pd
import streamlit as st

COLUMN_ORDER = \
    [
        'ticket_url', 'data_rep', 'counts_url', 'rep', 'company', 'ticket_id', 'tbpdb_campaign', 'ship_date', 'ihd', 'fe_status', 'adorbit_qty', 'ticket_summary',
        'tbpdb_status', 'data_file_status', 'status', 'ihd_month', 'parent_tbpdb_status'
    ]


def _clean_up_open_tickets(open_tickets):
    print(open_tickets[open_tickets['ticket_id'] == 123986])
    open_tickets = open_tickets[
        (open_tickets['product'].isin(['Solo Mailers']))
    ]
    open_tickets = open_tickets[
        ~(open_tickets['tbpdb_status'].isin(['Awaiting Closer IHD']))
    ]

    if 'counts_sent' not in open_tickets.columns:
        open_tickets['counts_sent'] = None

    open_tickets.loc[
        (open_tickets['data_file_status'] == 'Waiting on Map/List Approval') &
        (open_tickets['counts_sent'].isna()),
        'counts_sent'
    ] = pd.to_datetime('today').normalize()

    open_tickets.loc[pd.to_datetime(open_tickets['ihd']) < pd.to_datetime('today').normalize(), 'ihd'] = pd.to_datetime(
        'today').normalize()

    if 'counts_approved' not in open_tickets.columns:
        open_tickets['counts_approved'] = None

    open_tickets.loc[
        (open_tickets['data_file_status'] == 'Counts/Map Approved-Need to Create Files') &
        (open_tickets['counts_approved'].isna()),
        'counts_approved'
    ] = pd.to_datetime('today').normalize()

    open_tickets['parent_tbpdb_status'] = open_tickets['tbpdb_status']

    open_tickets.loc[
        open_tickets['tbpdb_status'].isin(
            ["Confirm Map", "Confirm Previous Data", "Confirm Status", "Need Client Data", "Blocked by Data Request"]),
        'parent_tbpdb_status'
    ] = '*Bump Reps*'

    open_tickets.loc[
        open_tickets['tbpdb_status'].isin(
            ["Build Count", "Build Map", "Use Previous Data", "Have Client Data"]),
        'parent_tbpdb_status'
    ] = 'Counts'

    open_tickets.loc[
        open_tickets['tbpdb_status'].isin(["Run Data", "Run Workflow"]),
        'parent_tbpdb_status'
    ] = 'Run Data'

    open_tickets['priority'] = 0
    open_tickets.loc[(open_tickets['production_ready'] >= 0) & (
                pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(
            days=14)), 'priority'] = 1
    open_tickets.loc[(open_tickets['production_ready'] >= 1) & (
                pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(days=7)), 'priority'] = 2
    open_tickets.loc[(open_tickets['production_ready'] >= 1) & (
                pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(days=4)), 'priority'] = 3
    open_tickets.loc[(open_tickets['production_ready'] >= 2) & (
                pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(days=3)), 'priority'] = 4
    open_tickets.loc[(open_tickets['production_ready'] >= 3) & (
                pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(days=3)), 'priority'] = 5
    open_tickets.loc[
        (open_tickets['production_ready'] >= 1) &
        (
                (open_tickets['ticket_summary'].str.contains('ASAP', case=False, na=False)) |
                (pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(days=1)) | (pd.to_datetime(open_tickets['ihd']) < pd.Timestamp.now() + pd.Timedelta(days=1)) |
                (
                    (pd.to_datetime(open_tickets['ship_date']) <= pd.Timestamp.now() + pd.Timedelta(days=1)) &
                    (open_tickets['adorbit_qty'] < 5000)
                )
        )
        , 'priority'] = 6

    open_tickets.loc[
        open_tickets['parent_tbpdb_status'].isin(["Run Data"]), 'priority'
    ] = open_tickets['priority'] + 2

    open_tickets = open_tickets.sort_values(by=['priority', 'ship_date', 'adorbit_qty', 'ihd'],
                                            ascending=[False, True, False, True])
    open_tickets['priority'] = range(len(open_tickets))
    open_tickets['priority'] = 100 * ((len(open_tickets) - open_tickets['priority']) / len(open_tickets))

    open_tickets.loc[pd.to_datetime(open_tickets['ihd']) < pd.to_datetime('today').normalize(), 'ihd'] = pd.to_datetime(
        'today').normalize()
    print(open_tickets[open_tickets['ticket_id'] == 123986])
    print('done')
    return open_tickets


def run_query(qry):
    conn = st.connection("snowflake")
    cur = conn.cursor()

    try:
        # 1. Execute the UPDATE query
        update_query = qry
        cur.execute(update_query)
    except Exception as e:
        return False, str(e)
    return True, None

# Function to connect to Snowflake and fetch data
def fetch_data_from_snowflake():
    """Fetch data from multiple Snowflake tables."""
    # Create Snowflake connection
    conn = st.connection("snowflake")


    # Example SQL queries to fetch data from multiple tables
    tables = [
        'tbp_audit',
        'tbp_open_tickets_r2',
        'tbp_closed_tickets',
        'tbp_companies',
        'tbp_data_requests_r2',
    ]
    # Fetch data from each query and store them in dataframes
    dfs = {}
    for t in tables:
        q = f'select * from TBP.MAIN.{t}'
        if q.strip():  # Ensure the query isn't empty
            df = pd.read_sql(q, conn)
            if 'open_tickets' in t.lower():
                df = _clean_up_open_tickets(df)
            dfs[t] = df


    return dfs


# Cache the data for 10 minutes (600 seconds)
@st.cache_data(ttl=600)
def get_cached_data(table_name):
    """Return cached Snowflake data."""
    for name, df in fetch_data_from_snowflake().items():
        if table_name.lower() in name.lower():
            if 'ship_date' in df.columns:
                df['ship_date'] = pd.to_datetime(df['ship_date']).dt.strftime('%B %d %Y')

            if 'ihd' in df.columns:
                df['raw_ihd'] = pd.to_datetime(df['ihd'])
                df['ihd'] = pd.to_datetime(df['ihd'])
                if 'product' in df.columns:
                    df['ihd_month'] = df['product'] + ' for ' + df['ihd'].apply(
                        lambda x: x.replace(day=1).strftime('%B, %Y'))

                df['ihd'] = pd.to_datetime(df['ihd']).dt.strftime('%B %d %Y')

            if 'ticket_id' in df.columns:
                df['counts_url'] = 'http://localhost:8501/counts_creator?ticket_id=' + df['ticket_id'].astype(str)

                def create_clickable_url(ticket_id):
                    return f'https://tbp.adorbit.com/tickets/ticket/?id={ticket_id}'

                df['ticket_url'] = df['ticket_id'].apply(create_clickable_url)

            if 'tbpdb_status' in df.columns and 'status' in df.columns:
                df['fe_status'] = df['tbpdb_status'] + ' | ' + df['status']
            elif 'data_file_status' in df.columns and 'status' in df.columns:
                df['fe_status'] = df['data_file_status'] + ' | ' + df['status']
            if 'adorbit_qty' in df.columns:
                df['adorbit_qty'] = pd.to_numeric(df['adorbit_qty'],
                                                  errors='coerce')  # Convert to numeric, invalid parsing will be set to NaN
                df['adorbit_qty'] = df['adorbit_qty'].apply(
                    lambda x: "{:,.0f}".format(x) if pd.notnull(x) else x)  # Format the numeric values



            global COLUMN_ORDER
            columns_found =[]
            for co in COLUMN_ORDER:
                if co in df.columns:
                    columns_found.append(co)
            df = df[columns_found + [x for x in df.columns if x not in columns_found]]
            return df


def apply_data_request_styling(x):
    _column_order = list(x.columns)

    # Create an empty DataFrame with the same shape as the input DataFrame
    styles = pd.DataFrame('', index=x.index, columns=x.columns)

    # Set the background color for the entire row
    for i in range(len(x)):
        if x.iloc[i, _column_order.index('report_status')] == 'Report Done':  # Condition based on the value in the first column
            styles.iloc[i, :] = 'background-color: #dbdbdb; color: black'  # Apply style to the entire row
        if x.iloc[i, _column_order.index('report_status')] == 'Report Sent':  # Condition based on the value in the first column
            styles.iloc[i, :] = 'background-color: #ddfacf; color: black; font-weight: bold'  # Apply style to the entire row
        if x.iloc[i, _column_order.index('report_status')] == 'Unassigned':  # Condition based on the value in the first column
            styles.iloc[i, :] = 'background-color: #fbfca2; color: black; font-weight: bold'  # Apply style to the entire row
    return styles


def apply_main_ticket_styling(x):

    _column_order = list(x.columns)

    # Create an empty DataFrame with the same shape as the input DataFrame
    styles = pd.DataFrame('', index=x.index, columns=x.columns)

    # Set the background color for the entire row
    for i in range(len(x)):
        if x.iloc[i, _column_order.index('parent_tbpdb_status')] == 'Counts':  # Condition based on the value in the first column
            styles.iloc[i, :] = 'background-color: #ebd8ab; color: black; font-weight: bold'  # Apply style to the entire row

        if x.iloc[i, _column_order.index(
                'parent_tbpdb_status')] == 'Run Data':  # Condition based on the value in the first column
            styles.iloc[i, :] = 'background-color: #91f086; color: black; font-weight: bold'  # Apply style to the entire row


    fe_index = _column_order.index('fe_status')
    # Apply the styles conditionally based on the value in the column
    styles.iloc[:, fe_index] = [
        'background-color: #f7d2d2; color: black; font-weight: bold' if 'approved' in str(v).lower() else
        'background-color: #f2746b; color: black; font-weight: bold' if 'inkjet' in str(v).lower() else
        'background-color: #f0a5a5; color: black; font-weight: bold' if 'tbp' in str(v).lower() else

        ''
        for v in x.iloc[:, fe_index]
    ]


    fe_index = _column_order.index('ship_date')
    # Get today's date
    today = datetime.now()

    # Apply formatting based on the conditions
    styles.iloc[:, fe_index] = [
        'background-color: #fad2cf; color: black; font-weight: bold' if pd.to_datetime(v) <= today else
        'background-color: #f0a5a5; color: red; font-weight: bold' if 'tbp' in str(v).lower() else
        ''
        for v in x.iloc[:, fe_index]
    ]


    fe_index = _column_order.index('adorbit_qty')
    # Get today's date
    today = datetime.now()

    # Apply formatting based on the conditions
    styles.iloc[:, fe_index] = [
        'background-color: white; color: black; font-weight: bold; font-size: 25' if len(str(v)) > 1 else
        'color: red; background-color: white; font-weight: bold; font-size: 25'
        ''
        for v in x.iloc[:, fe_index]
    ]


    return styles

def apply_closed_ticket_styling(x):
    _column_order = list(x.columns)

    # Create an empty DataFrame with the same shape as the input DataFrame
    styles = pd.DataFrame('', index=x.index, columns=x.columns)
    fe_index = _column_order.index('adorbit_qty')

    # Apply formatting based on the conditions
    styles.iloc[:, fe_index] = [
        'background-color: white; color: black; font-weight: bold; font-size: 25' if len(str(v)) > 1 else
        'color: red; background-color: white; font-weight: bold; font-size: 25'
        ''
        for v in x.iloc[:, fe_index]
    ]


    return styles



def get_staging_parquet_file_as_df(snowflake_filename):
    test_qry = f"""
                                            SELECT * 
                                            FROM @FILE_DROP.CASSED/{snowflake_filename}
                                              (FILE_FORMAT => 'FILE_DROP.PARQUET');
                                        """
    conn = st.connection("snowflake")

    df = pd.read_sql(
        sql=
        test_qry
        ,
        con=conn
    )
    lod = df[df.columns[0]].tolist()
    final_lod = []
    for dict_as_string in lod:
        _dict = json.loads(dict_as_string)
        final_lod.append(_dict)
    pd.set_option('future.no_silent_downcasting', True)
    ret_df = pd.DataFrame(final_lod).replace('nan', np.nan)
    return ret_df