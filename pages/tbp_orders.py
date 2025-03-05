from datetime import datetime, timedelta
import streamlit as st
import pandas as pd

st.set_page_config(page_title="TBP Orders", layout="wide", initial_sidebar_state='collapsed')


conn = st.connection("snowflake")


orders = pd.read_sql(sql=
                         """
                            select * from TASTY_BYTES_SAMPLE_DATA.RAW_POS.OPEN_TICKETS where "status" like 'TBP%'
                         """
                     ,
                     con=conn
                     )

def create_clickable_url(ticket_id):
    return f'https://tbp.adorbit.com/tickets/ticket/?id={ticket_id}'

# Apply the function to the URL column to make the links clickable
orders['ticket_url'] = orders['ticket_id'].apply(create_clickable_url)

orders = orders[
    [
        'ticket_url',
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


orders['ship_date'] = pd.to_datetime(orders['ship_date'])
orders['ihd'] = pd.to_datetime(orders['ihd'])
# Define a function to categorize the dates
def categorize_date(ship_date):
    today = datetime.today()
    if ship_date.date() < today.date():
        return 'Before Today'
    elif today <= ship_date < today + timedelta(weeks=1):
        return 'In Next Week'
    elif today <= ship_date < today + timedelta(weeks=4):
        return 'In Next Month'
    else:
        return 'After Next Month'

# Apply the function to create a new column
orders['ship_date_cat'] = orders['ship_date'].apply(categorize_date)
orders['min_ship_date_per_cat'] = orders.groupby('ship_date_cat')['ship_date'].transform('min')

orders['ship_date'] = pd.to_datetime(orders['ship_date'])


# Create a date slider to filter 'ship_date' column
min_date = orders['ship_date'].min().date()
max_date = orders['ship_date'].max().date()

# Initialize session state for max_date if not already done
if 'slider_selected_max_date' not in st.session_state:
    st.session_state.slider_selected_max_date = (datetime.today() + timedelta(days=15)).date()


col1, col2, col3 = st.columns([1, 10, 1])

yesterday = (datetime.today() - timedelta(days=1)).date()
past_orders = orders[orders['ship_date'].dt.date <= yesterday]
if len(past_orders) > 0:
    with col1:
        if st.button(f"{len(past_orders)} ASAP Orders"):
            st.session_state.slider_selected_max_date = yesterday  # Set max date to yesterday
            st.rerun()

with col2:
    # Date slider to filter ship_date range with dynamic max_date
    start_date, end_date = st.slider(
        'Select a date range for Ship Date',
        min_value=min_date,
        max_value=max_date,  # Use dynamic max_date from session state
        value=(min_date, st.session_state.slider_selected_max_date),
        format="YYYY-MM-DD"
    )

next_month = orders[orders['ship_date'].dt.date <= (datetime.today() + timedelta(days=30)).date()]
if len(next_month) > 0:
    with col3:
        if st.button(f"{len(next_month)} orders in the next month."):
            st.session_state.slider_selected_max_date = (datetime.today() + timedelta(days=30)).date()
            st.rerun()



# Filter the DataFrame based on the selected date range
filtered_orders = orders[(orders['ship_date'] >= pd.to_datetime(start_date)) & (orders['ship_date'] <= pd.to_datetime(end_date))]

# Display the filtered DataFrame
# Calculate the number of days from today to the selected date range
days_to_end = (pd.to_datetime(st.session_state.slider_selected_max_date) - pd.to_datetime('today')).days

if days_to_end < 0:
    st.header(f"{len(filtered_orders)} Orders with an ASAP ship date.")
else:
    st.header(f"{len(filtered_orders)} Orders set to ship in the next {days_to_end} days")

# Get unique statuses for the current ship_date_cat
statuses = filtered_orders['status'].drop_duplicates().tolist()


# Define the number of columns you want
num_columns = len(statuses)  # You can adjust this number based on your preference
columns = st.columns(num_columns)

# List to store selected statuses
selected_statuses = []

# Loop through the statuses and create checkboxes in columns
for i, status in enumerate(statuses):
    # Determine which column the checkbox should go into
    column = columns[i % num_columns]

    # Create checkbox for each status
    if column.checkbox(f'({len(filtered_orders[filtered_orders["status"].isin([status])])}) {status} ', key=status):
        selected_statuses.append(status)

# Filter the DataFrame based on selected statuses
if selected_statuses:
    filtered_orders = filtered_orders[filtered_orders['status'].isin(selected_statuses)]
else:
    filtered_orders = filtered_orders  # Show the full DataFrame if no status is selected

# Display the filtered DataFrame
#st.dataframe(filtered_orders, hide_index=True)

# Set up the data editor with the LinkColumn for ticket_url and other columns as regular columns
filtered_orders = filtered_orders.sort_values(by='ship_date',ascending=True)
filtered_orders['ship_date'] = filtered_orders['ship_date'].dt.strftime('%B %d, %Y')
filtered_orders['ihd'] = filtered_orders['ihd'].dt.strftime('%B %d, %Y')

def color_status(val):
    color = 'white'  # Default text color
    background_color = 'black'
    if val == 'TBP - READY TO SHIP':
        color = 'white'
        background_color = '#e37168'
        return f'color: {color}; font-weight: bold; background-color: {background_color}; font-size: 50px'
    return f'color: {color}; font-weight: bold'

# Apply styling to the DataFrame using Pandas Styler
styled_df = filtered_orders.style.applymap(color_status, subset=['status'])


st.data_editor(
    styled_df,
    column_config={
        "ticket_url": st.column_config.LinkColumn(
            "Ticket URL",
            help="Click to view the ticket",
            validate=r"^https://[a-z]+\.adorbit\.com/ticket/\d+$",  # Regular expression to validate the URL
            max_chars=100,  # Limit the text shown
            display_text=r"ticket/\?id=(.*)"  # Display everything after 'ticket/'
        )
    },
    disabled=True,
    height=800,
    hide_index=True  # Hide the index
)

if selected_statuses:
    st.write(f'{len(filtered_orders)} records found in {selected_statuses}')
else:
    st.write(f'{len(filtered_orders)} records displayed')


