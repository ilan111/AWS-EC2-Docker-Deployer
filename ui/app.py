import streamlit as st
import requests
import time
import json

API_URL = "http://localhost:8000"

st.title("🚀 AWS EC2 Docker Deployer")

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

# Submit user request
def submit_request():
    if not prompt.strip():
        st.warning("Please enter a prompt first.")
        return

    # Reset previous state
    st.session_state.request_id = None
    st.session_state.ai_result = None
    st.session_state.confirmed = False
    st.session_state.aws_access = ""
    st.session_state.aws_secret = ""

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
        try:
            while True:
                time.sleep(1)
                poll = requests.get(f"{API_URL}/result/{st.session_state.request_id}")
                poll_result = poll.json()

                if poll_result["status"] == "done":
                    st.session_state.ai_result = json.loads(poll_result["result"])
                    st.success("✅ Configuration ready for review!")
                    break
                else:
                    st.info("⏳ AI is still processing...")
        except Exception as e:
            st.error(f"Error fetching result: {e}")

# Display AI-generated configuration and confirmation
if st.session_state.ai_result and not st.session_state.confirmed:
    st.subheader("🧠 AI Suggested Configuration")
    st.json(st.session_state.ai_result)

    if st.button("Confirm Configuration"):
        st.session_state.confirmed = True
        st.success("Configuration confirmed ✅")

# AWS credentials input and EC2 deployment
if st.session_state.confirmed:
    st.subheader("🔐 Enter Your AWS Credentials")
    st.session_state.aws_access = st.text_input("AWS Access Key ID", type="password", value=st.session_state.aws_access)
    st.session_state.aws_secret = st.text_input("AWS Secret Access Key", type="password", value=st.session_state.aws_secret)

    if st.button("Deploy EC2 Instance"):
        if not st.session_state.aws_access or not st.session_state.aws_secret:
            st.warning("Please fill in both credentials.")
        else:
            with st.spinner("Deploying EC2 instance..."):
                try:
                    payload = {
                        "request_id": st.session_state.request_id,
                        "aws_access_key": st.session_state.aws_access,
                        "aws_secret_key": st.session_state.aws_secret
                    }
                    response = requests.post(f"{API_URL}/create-ec2", json=payload)
                    # Try to parse JSON even on error
                    result = response.json()
                    if response.status_code == 200:
                        result = response.json()  # Only parse if 200 OK
                        if result["status"] == "failed":
                            st.error("❌ Deployment failed")
                        st.success("✅ EC2 deployment started successfully!")
                        st.json(result)
                    else:
                        # Try to get JSON if possible, otherwise fallback
                        try:
                            result = response.json()
                            st.error(f"❌ Deployment failed: {result.get('detail', 'Unknown error')}")
                        except ValueError:
                            st.error(f"❌ Deployment failed: {response.text}")
                except Exception as e:
                    st.error(f"Deployment failed: {e}")
