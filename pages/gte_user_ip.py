import streamlit as st
from flask import Flask, request
from threading import Thread
import requests
import time

app = Flask(__name__)

# Function to serve Flask
def run_flask():
    app.run(host='0.0.0.0', port=5000)

# Flask route to get the public IP of the user
@app.route('/get_ip', methods=['GET'])
def get_ip():
    # Make an external API call to get the user's public IP
    try:
        response = requests.get('https://api.ipify.org?format=json')
        if response.status_code == 200:
            ip_data = response.json()
            return ip_data['ip']
        else:
            return "Error: Unable to fetch IP"
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

# Function to get the IP of the user from Flask
def get_user_ip():
    try:
        response = requests.get("http://127.0.0.1:5000/get_ip")
        return response.text
    except requests.exceptions.RequestException as e:
        return f"Error: {e}"

# Start Flask server in a separate thread
flask_thread = Thread(target=run_flask)
flask_thread.daemon = True
flask_thread.start()

# Allow some time for the Flask server to start
time.sleep(2)

# Streamlit application
st.title('Streamlit App')

# Get the user's IP from the Flask route
user_ip = get_user_ip()

st.write(f'User IP Address: {user_ip}')
