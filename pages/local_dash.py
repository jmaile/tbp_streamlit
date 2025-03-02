# streamlit_app.py (Streamlit app)
import streamlit as st

# Set the page config to hide the sidebar by default
st.set_page_config(page_title="Streamlit with Dash", layout="wide", initial_sidebar_state="collapsed")

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
            <iframe src="http://192.168.4.229:8051/orders-data" width="100%" height="100%"></iframe>
        </body>
    </html>
""", height=1000)  # Set height to 0 as the iframe itself will handle the height
