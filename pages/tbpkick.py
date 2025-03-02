import openai
import re
import streamlit as st
from prompts import get_system_prompt
import pandas as pd

# Check if the user is authenticated
if 'authenticated' not in st.session_state or not st.session_state.authenticated:
    st.error("You must be logged in to access this page.")
    st.stop()  # Prevent further code execution if the user is not logged in


st.set_page_config(page_title="🧙 TBP Assistant", layout="wide")

# Initialize the chat messages history
openai.api_key = st.secrets.OPENAI_API_KEY
if "messages" not in st.session_state:
    # system prompt includes table information, rules, and prompts the LLM to produce
    # a welcome message to the user.
    st.session_state.messages = [{"role": "system", "content": get_system_prompt()}]

# Prompt for user input and save
if prompt := st.chat_input():
    st.session_state.messages.append({"role": "user", "content": prompt})

# display the existing chat messages
for message in st.session_state.messages:
    if message["role"] == "system":
        continue
    with st.chat_message(message["role"]):
        st.write(message["content"])
        if "results" in message:
            st.dataframe(message["results"])



GOOD_QS = [
    "Give me all records mailed to main street in CT",
    "how many records are in the dataset?",
    "how many records have we mailed to wethersfield, CT?",
    """
    select "name", count(*) as name_count
    from TASTY_BYTES_SAMPLE_DATA.RAW_POS.ML_MASTER
    where lower("state") like '%az%' and lower("name") not like '%homeowner%' and lower("name") not like '%resident%'
    group by "name"
    order by name_count desc
    limit 1
    """,
    "Top 10 state, city, zip that weve mailed",
    "Have we ever mailed '2395 WHITE OAK TRL'?"
]


# If last message is not from assistant, we need to generate a new response
if st.session_state.messages[-1]["role"] != "assistant":
    with st.chat_message("assistant"):
        response = ""
        resp_container = st.empty()
        for delta in openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages],
            stream=True,
        ):
            response += delta.choices[0].delta.get("content", "")
            resp_container.markdown(response)

        message = {"role": "assistant", "content": response}
        # Parse the response for a SQL query and execute if available
        sql_match = re.search(r"```sql\n(.*)\n```", response, re.DOTALL)
        if sql_match:
            sql = sql_match.group(1)
            print(sql)
            conn = st.connection("snowflake")
            message["results"] = conn.query(sql)
            df = pd.DataFrame(message["results"])
            st.dataframe(message["results"])
            #chart_drawer = ChartDrawer(df)
            #chart_drawer.draw_chart()

        st.session_state.messages.append(message)

# In tbpkick.py
if st.button("Logout"):
    st.session_state.authenticated = False
    st.success("You have logged out.")
    st.experimental_rerun()  # Re-run the app to show the login page again
