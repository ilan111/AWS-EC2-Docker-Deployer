import logging
import streamlit as st
import requests
import time
import os
import json
from dotenv import load_dotenv

log = logging.getLogger("streamlit")

load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="AWS EC2 Docker Deployer")

st.title("🚀 AWS EC2 Docker Deployer")

if not "GITHUB_TOKEN" in os.environ:
        st.warning(f"Please assign your OpenAI API key to 'GITHUB_TOKEN' variable inside .env file\n\nThen run 'docker compose up -d --build'")

st.info("""
**Before deploying, make sure you have done the following:**

* ✅ Create an **IAM User** in AWS and generate **Access Key** and **Secret Key** with full EC2 permissions.
* ✅ Create a **Key Pair** in AWS.
* ✅ Choose the **region** where this key pair exists and enter its **exact name** in the form.
""")

# Input prompt
prompt = st.text_input("Enter your request (e.g., 'Deploy nginx container on AWS')")

# Initialize session state
if "request_id" not in st.session_state:
    st.session_state.request_id = None
if "confirmed" not in st.session_state:
    st.session_state.confirmed = False
if "ai_result" not in st.session_state:
    st.session_state.ai_result = None
if "aws_access" not in st.session_state:
    st.session_state.aws_access = ""
if "aws_secret" not in st.session_state:
    st.session_state.aws_secret = ""
if "error" not in st.session_state:
    st.session_state.error = False

def display_chat_message(message, sender="ai"):
    if sender == "ai":
        st.markdown(
            f"""
            <div style="
                background-color:#171717;
                padding:10px 15px;
                border-radius:15px;
                margin:10px 0;
                max-width:100%;
                ">
                {message}
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:  # user
        st.markdown(
            f"""
            <div style="
                background-color:#303030;
                color:white;
                padding:10px 15px;
                border-radius:15px;
                margin:10px 0;
                max-width:100%;
                float:right;
                clear:both;
                ">
                {message}
            </div>
            """,
            unsafe_allow_html=True,
        )

def reset_session_state():
    st.session_state.request_id = None
    st.session_state.ai_result = None
    st.session_state.confirmed = False
    st.session_state.aws_access = ""
    st.session_state.aws_secret = ""
    st.session_state.error = False

# Submit user request
def submit_request():
    if not prompt.strip():
        st.warning("Please enter a prompt first.")
        return

    # Reset previous state
    reset_session_state()
    

    with st.spinner("Submitting your request..."):
        try:
            response = requests.post(f"{API_URL}/request", json={"text": prompt})
            result = response.json()
            st.session_state.request_id = result.get("request_id")
            st.success(f"✅ Request submitted successfully! ID: {st.session_state.request_id}")
        except Exception as e:
            st.error(f"Error submitting request: {e}")

st.button("Submit Request", on_click=submit_request)

# Polling for AI result
if st.session_state.request_id and not st.session_state.ai_result:
    with st.spinner("Waiting for AI configuration..."):
        placeholder = st.empty()
        try:
            while True:
                time.sleep(1)
                poll = requests.get(f"{API_URL}/result/{st.session_state.request_id}")
                poll_result = poll.json()

                if poll_result["status"] == "done":
                    st.session_state.ai_result = poll_result["result"]
                    placeholder.success("✅ Configuration ready for review!")
                    break
                else:
                    placeholder.info("⏳ AI is still processing...")
        except Exception as e:
            st.write(f"{poll_result}")
            st.error(f"Error fetching result: {e}")
            st.error(f"Please make sure you have configured OpenAI API key with 'GITHUB_TOKEN' environment variable")

# AWS credentials input and EC2 deployment
# Step: Display AI result and confirm
if st.session_state.ai_result and not st.session_state.confirmed:
    st.subheader("🧠 AI Suggested Configuration")
    display_chat_message(st.session_state.ai_result, sender="ai")

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Confirm Configuration", key="confirm_button"):
            st.session_state.confirmed = True
            st.success("Configuration confirmed ✅")
    with col2:
        if st.button("Go Back", key="go_back_button"):
            # Reset to initial state
            reset_session_state()
            st.rerun()

# AWS credentials input and EC2 deployment
if st.session_state.confirmed:
    st.subheader("🔐 Enter Your AWS Credentials")
    st.session_state.aws_access = st.text_input(
        "AWS Access Key ID", type="password", value=st.session_state.aws_access
    )
    st.session_state.aws_secret = st.text_input(
        "AWS Secret Access Key", type="password", value=st.session_state.aws_secret
    )

    if st.button("Deploy EC2 Instance", key="deploy_button"):
        if not st.session_state.aws_access or not st.session_state.aws_secret:
            st.warning("Please fill in both credentials.")
        else:
            st.session_state.error = False  # reset error before starting
            with st.spinner("Deploying EC2 instance..."):
                try:
                    payload = {
                        "request_id": st.session_state.request_id,
                        "aws_access_key": st.session_state.aws_access,
                        "aws_secret_key": st.session_state.aws_secret,
                    }

                    while True:
                        response = requests.post(f"{API_URL}/create-ec2", json=payload)

                        # Check HTTP status first
                        if response.status_code != 200:
                            # Try parsing JSON from error body
                            try:
                                error_data = response.json()
                                error_msg = error_data.get("error", response.text)
                            except ValueError:
                                error_msg = response.text or "Unknown error"
                            st.session_state.error = True
                            st.error(f"❌ Deployment failed: {error_msg}")
                            break

                        # Parse normal 200 OK JSON
                        try:
                            result = response.json()
                        except ValueError:
                            st.session_state.error = True
                            st.error(f"❌ Invalid response: {response.text}")
                            break

                        status = result.get("status")
                        if status in ("deploying", "in_progress"):
                            st.info("⏳ EC2 is being created...")
                            st.session_state.error = False
                            time.sleep(2)
                            continue
                        elif status in ("done", "deployed"):
                            st.session_state.error = False
                            st.success("✅ EC2 deployment completed!")
                            st.json(result)
                            break
                        elif status == "failed":
                            st.session_state.error = True
                            # Try to get detailed error from result
                            error_msg = result.get("error", "Unknown error")
                            st.error(f"❌ Deployment failed: {error_msg}")
                            break
                        # else:
                        #     st.session_state.error = True
                        #     st.error(f"❌ Unexpected response: {result}")
                        #     break

                except Exception as e:
                    st.session_state.error = True
                    st.error(f"Deployment failed: {str(e)}")
st.write(st.session_state.error)
# Only show detailed error if deployment actually failed
if st.session_state.error:
    try:
        time.sleep(1)
        response = requests.get(f"{API_URL}/result/{st.session_state.request_id}")

        if "application/json" in response.headers.get("Content-Type", ""):
            error_data = response.json()
            st.write(error_data)
        else:
            error_data = {"error": response.text or "Unknown error"}

        # Handle nested JSON in `result`
        if "result" in error_data and isinstance(error_data["result"], str):
            try:
                nested = json.loads(error_data["result"])
                error_msg = nested.get("error", error_data["result"])
            except json.JSONDecodeError:
                error_msg = error_data["result"]
        else:
            error_msg = error_data.get("error", "Unknown error")

        st.error(f"❌ Deployment failed: {error_msg}")

    except Exception as e:
        st.error(f"Failed to retrieve error details: {e}")
