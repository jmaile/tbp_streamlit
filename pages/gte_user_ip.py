import streamlit as st
from flask import Flask, request
from threading import Thread

app = Flask(__name__)

# Function to serve Flask
def run_flask():
    app.run(host='0.0.0.0', port=5000)

@app.route('/get_ip', methods=['GET'])
def get_ip():
    ip_address = request.remote_addr
    return ip_address

def get_user_ip():
    import requests
    response = requests.get("http://127.0.0.1:5000/get_ip")
    return response.text

# Start Flask server in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Streamlit application
st.title('Streamlit App')

user_ip = get_user_ip()

st.write(f'User IP Address: {user_ip}')
