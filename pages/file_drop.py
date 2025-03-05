import io
import time
from datetime import datetime
from pprint import pprint

import numpy as np
import pyarrow
import streamlit as st
import os
import pandas as pd

# Set up the page layout and styling
st.set_page_config(
    page_title="Professional File Upload",
    page_icon="📁",
    layout="wide"
)


conn = st.connection("snowflake")

@st.cache_data
def load_data_from_db():
    return pd.read_sql(sql='select * from TASTY_BYTES_SAMPLE_DATA.RAW_POS.COMPANY', con=conn)


df = load_data_from_db()


import streamlit as st

# Create two columns: one for the image and one for the title
col1, col2 = st.columns([1, 10])  # Adjust the column widths as needed
with col1:
    logo_path = r"https://jmaile.github.io/images/tbp_yellow_logo.jpg"  # Replace with your logo file path
    st.image(logo_path, width=100)  # Adjust the width as needed

with col2:
    st.title("TBP File Drop")

# Instructions
st.write(
    """
    - **Step 1:** Upload your files below. The supported formats are `.csv`, `.xlsx`, and `.txt`.

    - **Step 2:** For each file, select the company to associate it with.

    - **Step 3:** Once you've uploaded the file and selected the appropriate company, click "Submit" to upload the data.
    """
)

# Sample company list (you can modify this list as needed)
company_list = set(df['company'].tolist())

# Initialize session state to store file selections and company selections
if 'file_data' not in st.session_state:
    st.session_state.file_data = {}

uploaded_files = st.file_uploader(
    "Drag and Drop or Click to Select Files",
    accept_multiple_files=True,  # Allows multiple files to be uploaded
    type=["csv", "xlsx", "txt"]  # Accepting these file types
)

@st.dialog("Preview", width='large')
def open_df_modal(df):
    df = pd.concat(
        [
            df.head(10),
            df.tail(10),
        ]
    )
    st.write(df)

# Function to get file creation date
def get_file_creation_date(file):
    # Save the file temporarily to access its metadata
    with open(file.name, "wb") as f:
        f.write(file.getbuffer())

    # Get file creation time (works on local system, may vary by OS)
    creation_time = os.path.getctime(file.name)

    # Convert to a human-readable format
    readable_time = time.ctime(creation_time)
    return readable_time


def get_uploaded_file_as_df(uploaded_file):
    # Read the file's bytes
    bytes_data = uploaded_file.read()
    dfs = {}
    _filename =  str(uploaded_file.name).rsplit('.', 1)[0]
    # Display the filename and raw bytes (optional)

    # Use io.BytesIO to convert bytes to a file-like object and read into a pandas DataFrame
    file_like = io.BytesIO(bytes_data)

    # Check file type and read accordingly
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(file_like)
        dfs[_filename] = df
    elif uploaded_file.name.lower().endswith('.xlsx'):

        sheet_dict = pd.read_excel(file_like, sheet_name=None)  # Returns a dictionary of DataFrames

        # Cycle through all the sheets
        for sheet_name, df in sheet_dict.items():
            _filename = str(uploaded_file.name).rsplit('.', 1)[0]+ '_SHEET_' + sheet_name.upper().replace('SHEET','')
            dfs[_filename] = df
    else:
        st.error(f'Invalid file {uploaded_file.name}')

    return dfs


def push_dataframe_to_snowflake_staging(df, filename):
    import snowflake as sf
    from snowflake import connector
    # Establish Snowflake connection
    conn = st.connection("snowflake")

    temp_file_path = f'/tmp/TBP_FD_{datetime.now().strftime("%y%m%d")}_{filename}.pqt'
    try:
        df.to_parquet(temp_file_path)
    except Exception as e:
        df.astype(str).to_parquet(temp_file_path)

    # Define the stage name (assuming a stage exists in Snowflake)
    stage_name = '@TASTY_BYTES_SAMPLE_DATA.RAW_POS.TBPDB_PYTHON'


    # Execute the PUT command to stage the CSV data
    cursor = conn.cursor()
    put_command = f"PUT 'file://{temp_file_path}' {stage_name};"
    cursor.execute(put_command)


# Handle file upload and company selection for each uploaded file
if uploaded_files:
    for i, uploaded_file in enumerate(uploaded_files):

        with st.container(border=True):

            # Create two columns side by side: one for file name and one for company selection
            col1, col2 = st.columns([3, 1])

            # File name (col1)
            file_previews = get_uploaded_file_as_df(uploaded_file)
            creation_date = get_file_creation_date(uploaded_file)
            st.markdown(f"<h3 style='text-align: left;'>'{uploaded_file.name}'</h3>", unsafe_allow_html=True)

            for filename, found_df  in file_previews.items():
                if len(found_df) == 0:
                    st.error(f'No valid records found for {filename}')
                    continue
                st.divider()
                st.markdown(f"<h5 style='text-align: left;'>{filename}</h5>", unsafe_allow_html=True)
                st.markdown(f"<h7 style='text-align: left;'>Created on {creation_date} | {len(found_df)} records found</h7>", unsafe_allow_html=True)

                col1, col2, col3 = st.columns([3, 3, 1])
                with col1:
                    company_selection = st.selectbox(
                        label='Assign Company',
                        options=[''] + list(company_list),
                        key=f"company{filename}_{i}"  # Unique key to store the selection in session_state
                    )

                with col2:
                    campaign_selection = st.selectbox(
                        label='Assign Campaign',
                        options=('', 'Current Client', 'Prospect'),
                        key=f"campaign_{filename}_{i}"  # Unique key to store the selection in session_state
                    )

                if st.button(f"Preview", key=f"df_button_{filename}_{i}"):
                    open_df_modal(found_df)

                # Store the selected company and file in session state
                st.session_state.file_data[filename] = {
                    "file_name": uploaded_file.name,
                    "company": company_selection,
                    "campaign": campaign_selection,
                    "file": uploaded_file,
                    "creation_date": creation_date,
                    "found_df": found_df.to_dict('records'),
                }

            st.divider()

# Submit button to process all files and companies

if len(st.session_state.file_data) > 0:

    if st.button(f"Submit {len(st.session_state.file_data)} Files"):

        df = pd.DataFrame(
            list((st.session_state.file_data.values()))
        )

        df = df.replace("", np.nan)
        unassigned_files = []

        for file_name, data_dict in st.session_state.file_data.items():
            if data_dict['company'] != data_dict['company'] or data_dict['company'] == None or len(str(data_dict['company'])) == 0:
                st.error(f'{data_dict["file_name"]} is missing Company designation')
                continue
            if data_dict['campaign'] != data_dict['campaign'] or data_dict['campaign'] == None or len(str(data_dict['campaign'])) == 0:
                st.error(f'{data_dict["file_name"]} is missing Campaign designation')
                continue
            found_df = pd.DataFrame(data_dict['found_df'])
            found_df['tbpfd_company'] = data_dict['company']
            found_df['tbpfd_campaign'] = data_dict['campaign']
            found_df['tbpfd_filename'] = file_name
            push_dataframe_to_snowflake_staging(found_df,filename)

            st.dataframe(found_df,height=100)
            st.success(f"{len(found_df)} records from {file_name} has been successfully pushed to Snowflake!")

# Footer or additional information
st.write("Made with ❤️ by TBP")
