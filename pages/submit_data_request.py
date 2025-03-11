import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders


# Function to send email
def send_email(name, email, message, files):
    # Your SMTP email server configuration
    sender_email = "contact@justicemaile.com"  # Replace with your email
    receiver_email = "justice@thebestpostcards.com"  # Replace with recipient's email
    password = "qglw9ywvt6e5ze8v"  # Replace with your email password

    # Create the email object
    msg = MIMEMultipart()
    msg['From'] = f'TBP Database <tbpdb@fastmail.com>'  # Set the From name and email address
    msg['To'] = receiver_email
    msg['Subject'] = f"New Submission from {name}"

    # Body of the email
    body = f"Name: {name}\nEmail: {email}\nMessage:\n{message}"
    msg.attach(MIMEText(body, 'plain'))

    # Handle file upload correctly
    for file in files:
        # Create a MIMEBase object for the attachment
        part = MIMEBase('application', 'octet-stream')

        # Read the content of the uploaded file
        file_content = file.read()
        part.set_payload(file_content)

        # Encode the file to base64
        encoders.encode_base64(part)

        # Add the filename to the header
        part.add_header('Content-Disposition', f"attachment; filename={file.name}")

        # Attach the file to the email
        msg.attach(part)

    # Send the email
    try:
        with smtplib.SMTP_SSL('smtp.fastmail.com', 465) as server:  # Use your email provider's SMTP server
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
        st.success("Your message and attachment have been sent successfully!")
    except Exception as e:
        st.error(f"Error sending email: {e}")


# Streamlit form
def app():
    st.title("Submit a Data Request")

    # Form to capture user input
    with st.form(key='contact_form'):
        name = st.text_input("Rep")
        name = st.text_input("Company")
        name = st.text_input("Type")
        name = st.text_input("Priority")
        name = st.text_input("Assignee")
        email = st.text_input("Your Email")
        message = st.text_area("Message")
        ___ = st.text_area("GPT Interpretation")
        attachment = st.file_uploader("Attach a file", accept_multiple_files=True)

        submit_button = st.form_submit_button("Submit")

        if submit_button:
            if attachment:
                # Ensure the user uploads no more than 20 files
                if len(attachment) > 5:
                    st.warning("You can only upload up to 5 files. Please select fewer files.")
                else:
                    # Send email with the attachment and form data
                    send_email(name, email, message, attachment)
            else:
                st.warning("Please upload at least one file.")


app()
