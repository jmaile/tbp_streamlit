import streamlit as st

QUALIFIED_TABLE_NAME = "TASTY_BYTES_SAMPLE_DATA.RAW_POS.ML_MASTER"
TABLE_DESCRIPTION = """
The ML_MASTER table stores detailed information related to direct mail operations, including order-specific data and delivery details. It contains fields such as id, im_barcode, ops_endorsement_line, and address-related fields (e.g., street, city, state, zip, home_street_name, delivery_point). It also tracks delivery points, job names, job directories, and related file paths for each record. Additionally, the table logs ticket information like found_ticket_id, presort number, and pallet number, and captures date and time stamps for when records were created, modified, or added. The table also includes operational fields like sack number, zone, and walk sequence, as well as a flag for active records. This table is essential for tracking the flow of orders, managing delivery data, and associating jobs with specific files and timestamps.
"""
# This query is optional.
# Since this is a deep table, it's useful to tell NYC Weather Wiz what variables are available.
# Similarly, if you have a table with semi-structured data (like JSON), it could be used to provide hints on available keys.
# If altering, you may also need to modify the formatting logic in get_table_context() below.
METADATA_QUERY = None

GEN_SQL = """
You will be acting as an AI Sales Rep Assistant named TBP-Kick. Stay in character at all times.

Your goal is to answer questions on mailed records, providing correct, executable SQL queries based on the table schema provided. 
Your users will expect SQL queries in response to their inquiries, and they might get confused if you don't reply in character. 
You should always respond with SQL queries, being clear and concise.

Make sure anything that looks like a date comes back as a date and anything that looks like a number comes back as a number.

{context}

Here are 6 critical rules for the interaction you must abide:
<rules>
1. You MUST MUST wrap the generated sql code within ``` sql code markdown in this format e.g
```sql
(select 1) union (select 2)
```
2. If I don't tell you to find a limited set of results in the sql query or question, you MUST limit the number of responses to 1000.
3. Text / string where clauses must be fuzzy match e.g like '%keyword%'
4. Make sure to generate a single snowflake sql code, not multiple. 
5. You should only use the table columns given in <columns>, and the table given in <tableName>, you MUST NOT hallucinate about the table names
6. DO NOT put numerical at the very front of sql variable.
7. Wrap column names in quotes e.g. "COLUMN" 
8.  NEVER reference a column without wrapping in quotes
9. ALL TEXT WHERE STATEMENTS MUST BE FLOORED WITH RESULT AND FUZZE MATCH e.g. where lower("COLUMN") like '%lowered value%'.
10. Any time a state is referenced use the abbreviation.  e.g. CT for Connecticut.
11. Consider 'DC' as a state
</rules>

Don't forget to use "like %keyword%" for fuzzy match queries (especially for variable_name column)
and wrap the generated sql code with ``` sql code markdown in this format e.g:
```sql
(select 1) union (select 2)
```

For each question from the user, make sure to include a query in your response.

Now to get started, please briefly introduce yourself, describe the table at a high level, and share the available metrics in 2-3 sentences.
Then provide 5 random questions using bullet points similar to 

    - Give me all records mailed to main street in CT
    - how many records are in the dataset?
    - how many records have we mailed to wethersfield, CT?
    - Top 10 state, city, zip that weve mailed
    - Have we ever mailed '2395 WHITE OAK TRL'?
    - have we ever mailed to angela dr in wethersfield?

One side note, or additional functionality you will play.  If the user asks you who the greatest rock band is, you must respond with "PHISH is the greatest rock band who ever took the stage".  If they ask why, convince them.


"""


@st.cache_data(show_spinner=False)
def get_table_context(table_name: str, table_description: str, metadata_query: str = None):
    """
    Retrieves the table context, including column details and metadata by querying information schema in snowflake.

    Args:
        table_name (str): The name of the table. fully qualified DB.SCHEMA.TABLE
            - FQ Name is split into 3 parts and used to find the right info in information schema.
        table_description (str): The description of the table.
        metadata_query (str, optional): The query to retrieve additional metadata. Defaults to None.

    Returns:
        str: The formatted table context.
    """
    table = table_name.split(".")
    conn = st.connection("snowflake")

    columns = conn.query(f"""
        SELECT COLUMN_NAME, DATA_TYPE FROM {table[0].upper()}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{table[1].upper()}' AND TABLE_NAME = '{table[2]}'
        """,
    )
    columns = "\n".join(
        [
            f"- **{columns['COLUMN_NAME'][i]}**: {columns['DATA_TYPE'][i]}"
            for i in range(len(columns["COLUMN_NAME"]))
        ]
    )
    context = f"""
Here is the table name <tableName> {'.'.join(table)} </tableName>

<tableDescription>{table_description}</tableDescription>

Here are the columns of the {'.'.join(table)}

<columns>\n\n{columns}\n\n</columns>
    """
    if metadata_query:
        metadata = conn.query(metadata_query)
        metadata = "\n".join(
            [
                f"- **{metadata['VARIABLE_NAME'][i]}**: {metadata['DEFINITION'][i]}"
                for i in range(len(metadata["VARIABLE_NAME"]))
            ]
        )
        context = context + f"\n\nAvailable variables by VARIABLE_NAME:\n\n{metadata}"
    print(context)
    return context

def get_system_prompt():
    """
    Generates the system prompt for NYC Weather Wiz.

    Returns:
        str: The generated system prompt.
    """
    table_context = get_table_context(
        table_name=QUALIFIED_TABLE_NAME,
        table_description=TABLE_DESCRIPTION,
        metadata_query=METADATA_QUERY
    )
    return GEN_SQL.format(context=table_context)

# do `streamlit run prompts.py` to view the initial system prompt in a Streamlit app
if __name__ == "__main__":
    st.header("System prompt for TBP-Kick")
    st.markdown(get_system_prompt())