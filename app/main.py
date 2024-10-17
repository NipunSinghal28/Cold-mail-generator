__import__('pysqlite3') 
import sys 
sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')
import streamlit as st
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from langchain_community.document_loaders import WebBaseLoader
from chains import Chain
from portfolio import Portfolio
import re

# Function to clean the extracted text
def clean_text(text):
    # Remove HTML tags
    text = re.sub(r'<[^>]*?>', '', text)
    # Remove URLs
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    # Remove special characters
    text = re.sub(r'[^a-zA-Z0-9 ]', '', text)
    # Replace multiple spaces with a single space
    text = re.sub(r'\s{2,}', ' ', text)
    # Trim leading and trailing whitespace
    text = text.strip()
    return text

# Function to send email
def send_email(sender_email, sender_password, receiver_email, email_content, subject):
    try:
        # Set up the Gmail server connection
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()

        # Login using sender's credentials
        server.login(sender_email, sender_password)

        # Create the email
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = receiver_email
        msg['Subject'] = subject
        msg.attach(MIMEText(email_content, 'plain'))

        # Send the email
        server.send_message(msg)
        server.quit()

        return True
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False

def create_streamlit_app(llm, portfolio):
    st.title("📧 Cold Mail Generator")

    # Screen 1: Enter URL and receiver's email
    url_input = st.text_input("Enter a URL:")
    receiver_email = st.text_input("Receiver's email:")

    # Submit button for Screen 1
    if st.button("Generate Emails"):
        try:
            # Load job data from URL
            loader = WebBaseLoader([url_input])
            data = clean_text(loader.load().pop().page_content)

            # Load portfolio and extract jobs
            portfolio.load_portfolio()
            jobs = llm.extract_jobs(data)

            # Generate cold emails for extracted jobs
            st.session_state.generated_emails = []
            for job in jobs:
                skills = job.get('skills', [])
                links = portfolio.query_links(skills)
                email = llm.write_mail(job, links)
                st.session_state.generated_emails.append(email)

            st.session_state.receiver_email = receiver_email
            st.session_state.current_screen = "email_selection"

        except Exception as e:
            st.error(f"An Error Occurred: {e}")

    # Screen 2: Select one of the generated emails
    if "current_screen" in st.session_state and st.session_state.current_screen == "email_selection":
        st.subheader("Select a Cold Email to Send")

        # Display a radio button selection for emails (maximum 5 options)
        selected_email = st.radio("Choose a cold email:", st.session_state.generated_emails[:5])

        if st.button("Next"):
            st.session_state.selected_email = selected_email
            st.session_state.current_screen = "email_sending"

    # Screen 3: Ask for sender's Gmail and password, then send the email
    if "current_screen" in st.session_state and st.session_state.current_screen == "email_sending":
        st.subheader("Selected Cold Email")
        st.write(st.session_state.selected_email)

        # Input sender's email and password
        sender_email = st.text_input("Enter your Gmail", value="", type="default")
        sender_password = st.text_input("Enter your Gmail password (use app password)", value="", type="password")

        if st.button("Send Email"):
            if sender_email and sender_password:
                subject = "Cold Email Application"  # Adjust as needed
                if send_email(sender_email, sender_password, st.session_state.receiver_email, st.session_state.selected_email, subject):
                    st.success("Email sent successfully!")
                    st.session_state.current_screen = "home"  # Fixed this line
            else:
                st.error("Please enter both your Gmail and password.")

    # Home Button to reset app
    if "current_screen" in st.session_state and st.session_state.current_screen == "home":
        if st.button("Back to Home"):
            # Reset all session states for a clean restart
            st.session_state.clear()
            st.experimental_rerun()

# Main function to run the Streamlit app
if __name__ == "__main__":
    # Initialize the chain and portfolio
    chain = Chain()
    portfolio = Portfolio()

    # Set Streamlit page config
    st.set_page_config(layout="wide", page_title="Cold Email Generator", page_icon="📧")

    # Run the Streamlit app
    create_streamlit_app(chain, portfolio)
