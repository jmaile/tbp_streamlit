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

    - **Step 3:** Once you've uploaded the file and selected the appropriate company, click "Submit" to proceed with the data.
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

st.divider()


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


def push_file_to_snowflake(df, filename):
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

def get_uploaded_file_as_df(uploaded_file):
    # Read the file's bytes
    bytes_data = uploaded_file.read()
    dfs = {}
    _filename =  str(uploaded_file.name).rsplit('.', 1)[0]
    # Display the filename and raw bytes (optional)
    st.write("Filename:", uploaded_file.name)

    # Use io.BytesIO to convert bytes to a file-like object and read into a pandas DataFrame
    file_like = io.BytesIO(bytes_data)

    # Check file type and read accordingly
    if uploaded_file.name.lower().endswith('.csv'):
        df = pd.read_csv(file_like)
        dfs[_filename] = df
        push_file_to_snowflake(df, uploaded_file.name)
    elif uploaded_file.name.lower().endswith('.xlsx'):

        sheet_dict = pd.read_excel(file_like, sheet_name=None)  # Returns a dictionary of DataFrames

        # Cycle through all the sheets
        for sheet_name, df in sheet_dict.items():
            _filename = str(uploaded_file.name).rsplit('.', 1)[0]+ '_SHEET_' + sheet_name.upper().replace('SHEET','')
            dfs[_filename] = df
            push_file_to_snowflake(df, _filename)
    else:
        st.error(f'Invalid file {uploaded_file.name}')

    return dfs


# Handle file upload and company selection for each uploaded file
if uploaded_files:
    for i, uploaded_file in enumerate(uploaded_files):

        # Create two columns side by side: one for file name and one for company selection
        col1, col2 = st.columns([3, 1])

        # File name (col1)
        file_previews = get_uploaded_file_as_df(uploaded_file)
        for filename, preview  in file_previews.items():
            st.markdown(f"<h5 style='text-align: left;'>{filename}</h5>", unsafe_allow_html=True)

            if st.button("Preview DF", key=f"df_button_{filename}_{i}"):
                open_df_modal(preview)
            # todo make a popup st.write(preview)
            creation_date = get_file_creation_date(uploaded_file)
            st.write(f"Created on {creation_date}")
            st.write(f"{len(preview)} records received")

            ass_comp, ass_camp = st.columns(2)

            with ass_comp:
                company_selection = st.selectbox(
                    label='Assign Company',
                    options=[''] + list(company_list),
                    key=f"company{filename}_{i}"  # Unique key to store the selection in session_state
                )

            with ass_camp:
                campaign_selection = st.selectbox(
                    label='Assign Campaign',
                    options=('', 'Current Client', 'Prospect'),
                    key=f"campaign_{filename}_{i}"  # Unique key to store the selection in session_state
                )


            # Store the selected company and file in session state
            st.session_state.file_data[filename] = {
                "file_name": uploaded_file.name,
                "company": company_selection,
                "campaign": campaign_selection,
                "file": uploaded_file,
                "creation_date": creation_date
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

        for file in df.to_dict('records'):
            if file['company'] != file['company'] or file['company'] == None or len(str(file['company'])) == 0:
                unassigned_files.append(f'{file["file_name"]} is missing Company designation')

            if file['campaign'] != file['campaign'] or file['campaign'] == None or len(str(file['campaign'])) == 0:
                unassigned_files.append(f'{file["file_name"]} is missing Campaign designation')

        if len(unassigned_files) > 0:
            for ste in unassigned_files:
                st.error(ste)
        else:
            # upload df and file to snowflake
            st.success("All files and companies have been successfully submitted!")

# Footer or additional information
st.write("Made with ❤️ by TBP")
