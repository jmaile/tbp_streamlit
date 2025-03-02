import streamlit as st
import pandas as pd
import plotly.express as px

# Placeholder: Replace this with actual data loading logic (e.g., using pandas.read_sql)
# For example, you can use a connection to your database to load the data into a DataFrame.
# data = pd.read_sql("SELECT * FROM TASTY_BYTES_SAMPLE_DATA.RAW_POS.COMPANY", conn)

# Sample data loading for demo purposes

if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.error("You must be logged in to access this page.")
    st.stop()  # Prevent further code execution if the user is not logged in

conn = st.connection("snowflake")

data = pd.read_sql(sql='select * from TASTY_BYTES_SAMPLE_DATA.RAW_POS.COMPANY', con=conn)


# Convert ship_date and date_ticket_update to datetime
data['ship_date'] = pd.to_datetime(data['ship_date'])
data['date_ticket_update'] = pd.to_datetime(data['date_ticket_update'])

# 1. **Aggregate Data by Rep**
agg_data = data.groupby('rep').agg(
    total_qty=('adorbit_qty', 'sum'),
    total_price=('gross_price', 'sum'),
    ticket_count=('ticket_id', 'count'),
    avg_price=('gross_price', 'mean')
).reset_index()

# 2. **Visualizations**
st.title('Company Dashboard')

# 2.1 **Bar chart for Total Quantity by Rep**
fig1 = px.bar(agg_data, x='rep', y='total_qty', title='Total Quantity by Rep')
st.plotly_chart(fig1)

# 2.2 **Bar chart for Total Gross Price by Rep**
fig2 = px.bar(agg_data, x='rep', y='total_price', title='Total Gross Price by Rep')
st.plotly_chart(fig2)

# 2.3 **Line chart for Average Price by Rep**
fig3 = px.line(agg_data, x='rep', y='avg_price', title='Average Price by Rep')
st.plotly_chart(fig3)

# 3. **Filters for Interactivity** (Optional: filter by Rep, Product, etc.)
rep_filter = st.selectbox('Select Rep', agg_data['rep'].unique())
filtered_data = data[data['rep'] == rep_filter]

# 4. **Display Filtered Data**
st.subheader(f"Data for {rep_filter}")
st.dataframe(filtered_data)

# 5. **Additional Metrics**
st.subheader('Aggregate Metrics')
st.write(agg_data)

# 6. **Add any more visualizations or metrics as needed**

# Run the Streamlit app using: streamlit run <filename.py>

