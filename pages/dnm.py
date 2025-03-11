import re

import streamlit as st
import snowflake.connector

SCHEMA_NAME = 'RAW_POS'
TABLE_NAME = 'DNM'

# Function to create table if not exists
def create_table_if_not_exists(conn):
    try:
        cursor = conn.cursor()

        # Ensure the schema is set in the session
        cursor.execute(f"USE SCHEMA {SCHEMA_NAME}")  # Set the schema here

        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                address_id STRING PRIMARY KEY,
                street STRING,
                city STRING,
                state STRING,
                zip_code STRING,
                created_at TIMESTAMP,
                updated_at TIMESTAMP
            )
        """)

    except Exception as e:
        st.error(f"Error creating table: {e}")
    finally:
        cursor.close()


st.title("Do Not Mail")


# If connection hasn't been created yet, create one
if 'conn' not in st.session_state:
    st.session_state.conn = st.connection("snowflake")

# Ensure the table exists
create_table_if_not_exists(st.session_state.conn)

# Streamlit form to enter address details
with st.form(key='address_form'):
    # Inputs for address
    street = st.text_input("Street Address")
    city = st.text_input("City")
    state = st.text_input("State")
    zip_code = st.text_input("ZIP Code")
    address_id = str(street) + str(state) + str(zip_code)
    address_id = re.sub(r'[^0-9A-Z.]', '', address_id.upper())
    # Submit button
    submit_button = st.form_submit_button(label='Submit')

# Handle form submission
if submit_button:

    try:
        cursor = st.session_state.conn.cursor()

        # Check if the address_id exists
        cursor.execute(f"""
            SELECT COUNT(*) FROM {SCHEMA_NAME}.{TABLE_NAME} WHERE address_id = '{address_id}'
        """)
        result = cursor.fetchone()
        count = result[0] if result else 0

        if count > 0:
            # If ID exists, replace the existing record with the new data and update the 'updated_at' field
            cursor.execute(f"""
                UPDATE {SCHEMA_NAME}.{TABLE_NAME}
                SET street = '{street}', city = '{city}', state = '{state}', zip_code = '{zip_code}', updated_at = CURRENT_TIMESTAMP
                WHERE address_id = '{address_id}'
            """)
            st.success(f"Address with ID {address_id} updated!")
        else:
            # If ID doesn't exist, insert a new record and set 'created_at' to CURRENT_TIMESTAMP
            cursor.execute(f"""
                INSERT INTO {SCHEMA_NAME}.{TABLE_NAME} (address_id, street, city, state, zip_code, created_at, updated_at)
                VALUES ('{address_id}', '{street}', '{city}', '{state}', '{zip_code}', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """)
            st.success(f"DNM ID {address_id} added.")

    except Exception as e:
        st.error(f"Error: {e}")
    finally:
        cursor.close()
