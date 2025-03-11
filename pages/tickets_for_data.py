import datetime
import re
import time
from pprint import pprint

import pandas as pd
import streamlit as st
import datetime
import calendar
import scripts
st.set_page_config(page_title="Tickets for Data", layout="wide",  initial_sidebar_state='collapsed')



open_tickets = scripts.snowflake_data.get_cached_data('open_tickets').sort_values(by='ihd', ascending=True)

main_tab, uploads_tab, dup_jobs_tab, attention_orders_tab = st.tabs(["Main", "Uploads", "Duplicate Jobs", "Jobs Needing Attention"])

# ----- MAIN DATA TAB ----------------------------------------------------------------------------------------------------
with main_tab:

    main_tab_orders = open_tickets[open_tickets['department'].isin(['Data', 'Shipping'])]
    min_date = pd.to_datetime(main_tab_orders['ihd']).min().date()
    max_date = (datetime.datetime.today() + datetime.timedelta(days=30)).date()

    if 'slider_selected_max_date' not in st.session_state:
        today = datetime.datetime.today()
        last_day_of_month = datetime.date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])
        st.session_state.slider_selected_max_date = last_day_of_month
        st.session_state.slider_selected_max_date = (datetime.datetime.today() + datetime.timedelta(days=7)).date()


    start_date, end_date = st.slider(
        'Select a date range for IHD',
        min_value=min_date,
        max_value=max_date,  # Use dynamic max_date from session state
        value=(min_date, st.session_state.slider_selected_max_date),
        format="YYYY-MM-DD"
    )


    col1, col2 = st.columns([1, 5])

    with col1:
        n_col1, n_col2 = st.columns([2, 4])
        with n_col1:
            today = datetime.datetime.today().date()
            three_days_later = (datetime.datetime.today() + datetime.timedelta(days=2))
            todays_priority = main_tab_orders[
                (main_tab_orders['ticket_summary'].str.contains('ASAP', case=False, na=False)) | (
                    (pd.to_datetime(main_tab_orders['ihd']) <= three_days_later) &
                    (main_tab_orders['production_ready'] > 0)
                )
            ]

            st.checkbox(f"Today's Priority ({len(todays_priority)})", key='daily_priority', value=False)
            if st.session_state.daily_priority:
                # If Daily Priority is checked, filter for orders in the next 3 days
                filtered_orders = todays_priority.copy()

            else:
                # If Daily Priority is not checked, filter by the selected date range
                filtered_orders = main_tab_orders[
                    (pd.to_datetime(main_tab_orders['ihd']) >= pd.to_datetime(start_date)) & (pd.to_datetime(main_tab_orders['ihd']) <= pd.to_datetime(end_date))]

        with n_col2:
            # Get unique statuses for the current ship_date_cat
            reps = sorted(filtered_orders['rep'].drop_duplicates().tolist())

            # Add an "ALL" option to the reps list
            reps_with_all = ['ALL'] + reps

            # Create a single select box with the option to select ALL
            sel_rep = st.selectbox("Select a Rep", reps_with_all)

            # Filter the orders based on the selected rep
            if sel_rep != 'ALL':
                filtered_orders = filtered_orders[filtered_orders['rep'] == sel_rep]
                statuses = filtered_orders[['parent_tbpdb_status', 'tbpdb_status']].drop_duplicates()
            else:
                statuses = filtered_orders[['parent_tbpdb_status', 'tbpdb_status']].drop_duplicates()


        st.divider()
        selected_statuses = []

        for parent_status, _df in statuses.groupby('parent_tbpdb_status'):
            emojis = {
                'Counts': "https://cdn-icons-png.flaticon.com/512/2584/2584580.png",
                'Run Data': "https://cdn-icons-png.flaticon.com/512/4357/4357499.png",
                '*Bump Reps*': "https://cdn-icons-png.flaticon.com/512/4161/4161834.png"
            }
            emoji = "https://cdn-icons-png.flaticon.com/512/626/626631.png"
            if parent_status in emojis:
                emoji = emojis[parent_status]

            st.markdown(
                f'<h5><img src="{emoji}" width="20" height="20" style="vertical-align: middle;"> {parent_status} ({len(filtered_orders[filtered_orders["parent_tbpdb_status"].isin([parent_status])])})</h5>',
                unsafe_allow_html=True
            )

            for i, status in enumerate(_df['tbpdb_status'].tolist()):
                # Create checkbox for each status
                if st.checkbox(
                        f'({len(filtered_orders[filtered_orders["tbpdb_status"].isin([status])])}) {status.title()} ',
                        key=status + parent_status):
                    selected_statuses.append(status)


        # Filter the DataFrame based on selected statuses
        if selected_statuses:
            filtered_orders = filtered_orders[filtered_orders['tbpdb_status'].isin(selected_statuses)]
        else:
            filtered_orders = filtered_orders  # Show the full DataFrame if no status is selected

    with col2:


        filtered_orders = filtered_orders.sort_values(by='priority', ascending=False)


        # Function to apply color based on multiple column conditions
        def apply_color_map(val, row):
            if row['parent_tbpdb_status'] == 'Counts':
                background_color = '#fadcb4'
                return f'color: {background_color}; font-weight: bold; font-size: 50px'

            if row['parent_tbpdb_status'] == 'Run Data':
                background_color = '#ed7777'
                return f'color: {background_color}; font-weight: bold; font-size: 50px'

            return ''


        #display_cols = ['_'] + display_cols

        filtered_orders.loc[filtered_orders['parent_tbpdb_status'] == 'Counts', '_'] = "https://raw.githubusercontent.com/jmaile/images/refs/heads/main/count.jpg"
        filtered_orders['ship_date'] = pd.to_datetime(filtered_orders['ship_date']).dt.strftime('%B %d %Y')
        filtered_orders['ihd'] = pd.to_datetime(filtered_orders['ihd']).dt.strftime('%B %d %Y')


        _length = len(filtered_orders)
        filtered_orders_df =filtered_orders.copy()
        # Apply the function to the DataFrame
        filtered_orders = filtered_orders.drop(columns=['counts_url']).style.apply(scripts.snowflake_data.apply_main_ticket_styling, axis=None)



        # Apply styling to the DataFrame using Pandas Styler
        #filtered_orders = filtered_orders[display_cols].style.applymap(color_status, subset=['fe_status', 'status'])
        user_selected_companies = st.dataframe(
            filtered_orders,
            column_config={
                "ticket_url": st.column_config.LinkColumn(
                    "Ticket URL",
                    help="Click to view the ticket",
                    validate=r"^https://[a-z]+\.adorbit\.com/ticket/\d+$",  # Regular expression to validate the URL
                    max_chars=100,  # Limit the text shown
                    display_text=r"ticket/\?id=(.*)"  # Display everything after 'ticket/'
                )
            },
            hide_index=True,
            on_select="rerun",
            selection_mode="multi-row",
            height=500
        )
        st.warning(f'{_length} tickets found.')

    # ----- SHOW COPMANY INFO

    _selected_companies = []
    for i, row in enumerate(filtered_orders_df.to_dict('records')):
        if i in user_selected_companies.selection.rows:
            _selected_companies.append(row['company_id'])

    if len(_selected_companies) > 0:

        ot = scripts.snowflake_data.get_cached_data('open_tickets').sort_values(by='ihd', ascending=True)
        future_date = pd.Timestamp.now() + pd.Timedelta(days=60)
        first_date_of_cutoff = future_date.replace(day=1) + pd.DateOffset(months=1)

        ot = ot[
            (ot['product'].isin(['Solo Mailers'])) &
            (pd.to_datetime(open_tickets['ihd']) < first_date_of_cutoff)
            ]
        ot = ot[ot['company_id'].isin(_selected_companies)]

        unique_months = ot.drop_duplicates(subset='ihd_month').sort_values(by='raw_ihd', ascending=True)[
            'ihd_month'].tolist()
        tabs = st.tabs([f"Open {month} ({len(ot[ot['ihd_month'] == month])})" for month in unique_months])
        # Loop over the unique months and display filtered DataFrame in the corresponding tab
        for i, ihd_month in enumerate(unique_months):
            with tabs[i]:
                # Filter the DataFrame for the current month
                _df = ot[ot['ihd_month'] == ihd_month]
                _df.loc[_df[
                            'parent_tbpdb_status'] == 'Counts', 'counts_url'] = 'http://localhost:8501/counts_creator?ticket_id=' + \
                                                                                _df['ticket_id'].astype(str)
                # Display the filtered DataFrame

                st.dataframe(
                    _df.style.apply(
                        scripts.snowflake_data.apply_main_ticket_styling, axis=None),
                    column_config={
                        "counts_url": st.column_config.LinkColumn(
                            "Counts URL",
                            help="Click to view the ticket",
                            validate=r"^https://[a-z]+\.adorbit\.com/ticket/\d+$",
                            # Regular expression to validate the URL
                            max_chars=100,  # Limit the text shown
                            display_text=r"Pull Count"  # Display everything after 'ticket/'
                        ),
                        "ticket_url": st.column_config.LinkColumn(
                            "Ticket URL",
                            help="Click to view the ticket",
                            validate=r"^https://[a-z]+\.adorbit\.com/ticket/\d+$",
                            # Regular expression to validate the URL
                            max_chars=100,  # Limit the text shown
                            display_text=r"ticket/\?id=(.*)"  # Display everything after 'ticket/'
                        )
                    },
                    hide_index=True
                )

        dr = scripts.snowflake_data.get_cached_data('data_requests').sort_values(by='date_created',
                                                                                 ascending=False)
        dr = dr[dr['company_id'].isin(_selected_companies)]
        if len(dr) == 0:
            st.divider()
            st.caption('NO DATA REQUESTS FOUND')
        else:
            st.divider()
            st.caption('Data Requests')

            dr['date_created'] = pd.to_datetime(dr['date_created']).dt.strftime('%B %d %Y')

            keep_cols = [
                'ticket_id',
                'company',
                'order_type',
                'date_created',
                'assignee',
                'notes',
                'report_status',
                'original_ticket_summary',
            ]
            dr_styled = dr[keep_cols].style.apply(
                scripts.snowflake_data.apply_data_request_styling, axis=None)

            user_selected_dr = st.dataframe(
                dr_styled,
                hide_index=True,
                width=5000,
                height=200,
                on_select="rerun",
                selection_mode="single-row",
            )
            for i, row in enumerate(dr.to_dict('records')):
                if i in user_selected_dr.selection.rows:
                    st.write(row)


        ct = scripts.snowflake_data.get_cached_data('closed_tickets').sort_values(by='ihd', ascending=False)
        ct = ct[(ct['product'].isin(['Solo Mailers']))]
        ct = ct[ct['company_id'].isin(_selected_companies)]

        if len(ct) > 0:
            st.divider()
            unique_months = ct.drop_duplicates(subset='ihd_month').sort_values(by='raw_ihd', ascending=False)[
                                'ihd_month'].tolist()[:3]

            for i, ihd_month in enumerate(unique_months):
                _df = ct[ct['ihd_month'] == ihd_month].drop(columns=['counts_url'])

                st.caption(f'({len(_df)}) Closed {ihd_month}')

                # Filter the DataFrame for the current month
                # Display the filtered DataFrame

                st.dataframe(
                    _df.style.apply(
                        scripts.snowflake_data.apply_closed_ticket_styling, axis=None),
                    hide_index=True,
                    column_config={
                        "ticket_url": st.column_config.LinkColumn(
                            "Ticket URL",
                            help="Click to view the ticket",
                            validate=r"^https://[a-z]+\.adorbit\.com/ticket/\d+$",
                            # Regular expression to validate the URL
                            max_chars=100,  # Limit the text shown
                            display_text=r"ticket/\?id=(.*)"  # Display everything after 'ticket/'
                        )
                    }
                )



# ----- MAIN DATA TAB ----------------------------------------------------------------------------------------------------

with uploads_tab:
    uploads_df = open_tickets[
                (open_tickets['status'].str.contains('ship', case=False)) |
                (
                    (open_tickets['status'] == 'done') &
                    (pd.to_datetime(open_tickets['ship_date']) == pd.to_datetime('today').normalize())
                 )
    ].drop(columns=['counts_url'])
    uploads_df = uploads_df[(pd.to_datetime(open_tickets['ship_date']) <= pd.to_datetime('today').normalize())]
    st.dataframe(
        uploads_df.style.apply(scripts.snowflake_data.apply_main_ticket_styling, axis=None),
        height=1000,
        hide_index=True,
        column_config={
            "ticket_url": st.column_config.LinkColumn(
                "Ticket URL",
                help="Click to view the ticket",
                validate=r"^https://[a-z]+\.adorbit\.com/ticket/\d+$",
                # Regular expression to validate the URL
                max_chars=100,  # Limit the text shown
                display_text=r"ticket/\?id=(.*)"  # Display everything after 'ticket/'
            )
        }
    )

with dup_jobs_tab:
    audit = scripts.snowflake_data.get_cached_data('tbp_audit')

    audit = audit[
                (audit['flag'].astype(str).str.contains('duplicate', case=False))
    ].sort_values(by='raw_ihd', ascending=False)[['ticket_id', 'ihd', 'flag']].rename(columns={'ihd': 'wb_import_date'})

    st.dataframe(
        audit,
        hide_index=True,
        width=5000
    )


with attention_orders_tab:
    audit = scripts.snowflake_data.get_cached_data('tbp_audit')

    audit = audit[
                ~(audit['flag'].astype(str).str.contains('duplicate', case=False)) &
                ~(audit['status'].isin(['Cancelled'])) &
                (pd.to_datetime(audit['ihd']) >= (datetime.datetime.today() - datetime.timedelta(days=30)))
    ].sort_values(by='raw_ihd', ascending=False)[['company', 'ticket_id', 'ihd', 'flag', 'summary', 'flag_description']]
    ack_jobs = st.dataframe(
        audit,
        height=500,
        hide_index=True,
        on_select="rerun",
        selection_mode="multi-row",
        width=5000
    )
    if len(ack_jobs.selection.rows) > 0:
        st.button(f'Mark {len(ack_jobs.selection.rows)} instances Acknowledged')

    st.divider()



# ----- COMPANY FILE ASSIGNMENT ------------------------------

def load_snowflake_tables():
    conn = st.connection("snowflake")

    files_pending_company_assignment = pd.read_sql(
        sql=
        """
            select * from TBP.FILE_DROP.CASSED_FILENAMES where "assigned_company_id" is null
        """
        ,
        con=conn
    )

    files_assigned = pd.read_sql(
        sql=
        """
            select * from TBP.FILE_DROP.CASSED_FILENAMES where "assigned_company_id" is not null
        """
        ,
        con=conn
    )

    return {
        'files_assigned': files_assigned,
        'files_pending_company_assignment': files_pending_company_assignment,
    }




snowflake_tables = load_snowflake_tables()
files_pending_company_assignment = snowflake_tables['files_pending_company_assignment']
files_assigned = snowflake_tables['files_assigned']


# Sample data of records (e.g., IDs, names, etc.)
files_pending_company_assignment = snowflake_tables['files_pending_company_assignment']

# Simulated function to suggest a company
def suggest_company(record):
    # Placeholder for a function that takes some time to compute
    return f"Suggested Company for {record}"

if 'record_index' not in st.session_state:
    st.session_state.record_index = 0

@st.fragment
def show_files_pending_assignment():
    # Initialize session state for record index if not already done
    all_companies = scripts.snowflake_data.get_cached_data('companies')
    def _match_company_to_row(row):
        scored_companies = all_companies.copy()[['company_name', 'state']]
        scored_companies['_score'] = 0

        # todo state
        original_filename = row['original_filename']
        common_words = ['service', 'heating', 'list', 'customer']
        for cw in common_words:
            original_filename = original_filename.upper().replace(cw.upper(),'')

        substrings = re.findall(r'[a-zA-Z]+', original_filename)
        for _company in scored_companies.to_dict('records'):
            company_substrings = re.findall(r'[a-zA-Z]+', _company['company_name'].upper())

            floored_company =  re.sub(r'[^a-zA-Z]', '', _company['company_name'].upper())

            if str(_company['state']).upper() in row['top_states'].upper():
                scored_companies.loc[scored_companies['company_name'] == _company['company_name'], '_score'] = scored_companies['_score'] + 5
            else:
                continue

            for s in substrings:
                if s.upper() in floored_company:
                    scored_companies.loc[scored_companies['company_name'] == _company['company_name'], '_score'] = scored_companies['_score'] + len(s)
                if s.upper() in company_substrings:
                    scored_companies.loc[scored_companies['company_name'] == _company['company_name'], '_score'] = scored_companies['_score'] + len(s)

        ret_companies = []
        for _company in scored_companies.sort_values(by='_score', ascending=False).to_dict('records'):
            if _company['company_name'] not in ret_companies:
                ret_companies.append(_company['company_name'])

        return ret_companies

    # Get current record from the session state index
    record_dict = files_pending_company_assignment.to_dict('records')[st.session_state.record_index]
    record = record_dict['original_filename']


    st.write(f"**{record}**")

    # Dropdown to select a company
    selected_company = st.selectbox(f"Assign company to {record}", _match_company_to_row(record_dict), key=f"{record}_selectbox")

    # Store the assignment in session state
    if 'assignments' not in st.session_state:
        st.session_state.assignments = {}

    # Update the assignment for the current record
    st.session_state.assignments[record] = selected_company

    # Display the record and the suggested company
    st.write(record_dict)


    company_id = \
    all_companies[all_companies['company_name'] == st.session_state.assignments[record]]['company_id'].tolist()[0]

    col1, col2 = st.columns([1, 20])
    with col1:
        st.button('Skip')
    with col2:
        if st.button(f'Assign "{record}" to {st.session_state.assignments[record]} ({company_id})'):
            qry =             f"""
                UPDATE TBP.FILE_DROP.CASSED_FILENAMES
                SET "assigned_company_id" = {company_id}
                WHERE "snowflake_filename" = '{record_dict['snowflake_filename']}';
                """
            st.code(
                qry
            )
            result, _ = scripts.snowflake_data.run_query(qry)
            if result:
                st.success(qry)
                st.button('Next')
            else:
                st.error(qry)
                st.error(_)

            st.session_state.record_index += 1  # Go to next record


with st.expander(f'{len(files_pending_company_assignment)} Files Pending Assignment | {len(files_assigned)} Files Assigned', expanded=False):
    show_files_pending_assignment()

