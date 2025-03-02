import streamlit as st

# Dummy credentials for illustration (replace with actual logic)
USER_CREDENTIALS = {
    "username": "admin",  # Example username
    "password": "password123"  # Example password
}

# Function to authenticate user
def authenticate(username, password):
    if username == USER_CREDENTIALS["username"] and password == USER_CREDENTIALS["password"]:
        return True
    return False

# Main function to handle login logic


def main():
    # Title for login page
    st.title("Login Page")

    # Check if the user is already authenticated
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        st.session_state.page = "tbpkick"
        st.rerun()  # Refresh to go to tbpkick page after successful login

    # Username and password input fields
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    # Login button
    if st.button("Login"):
        if authenticate(username, password):
            # Set session state to indicate the user is authenticated
            st.session_state.authenticated = True
            st.success("Logged in successfully!")
            st.switch_page("pages/tbpkick.py")

        else:
            st.error("Invalid credentials. Please try again.")



# Run the main function
if __name__ == "__main__":
    main()
