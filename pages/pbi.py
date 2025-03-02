# streamlit_app.py (Streamlit app)
import streamlit as st

# Set the page config to hide the sidebar by default
st.set_page_config(page_title="Power BI", layout="wide", initial_sidebar_state="collapsed")

# Inject the iframe using HTML and set full height and width
st.components.v1.html("""
    <html>
        <head>
            <style>
                /* Remove default Streamlit padding and margins */
                body, html {
                    margin: 0;
                    padding: 0;
                    height: 100%;
                    width: 100%;
                }
                /* Iframe takes full width and height */
                iframe {
                    border: none;
                    width: 100%;
                    height: 100vh;  /* Full height of the viewport */
                    display: block;  /* Remove any space below the iframe */
                }
            </style>
        </head>
        <body>
            <iframe src="https://app.powerbi.com/reportEmbed?reportId=87828c22-16f5-4c0a-8e65-7d45c83a2c77&autoAuth=true&ctid=6b5bfc53-2500-49de-b47e-4a00d13d2b0d" width="100%" height="100%"></iframe>
        </body>
    </html>
""", height=1000)  # Set height to 0 as the iframe itself will handle the height





