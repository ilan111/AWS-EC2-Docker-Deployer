import logging
import streamlit as st
import requests
import time
import os
import json
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
log = logging.getLogger("streamlit")

# Load environment variables
load_dotenv()
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Page configuration
st.set_page_config(page_title="AWS EC2 Docker Deployer", page_icon="🚀")

# Custom CSS for better styling
st.markdown("""
    <style>
    .stButton>button {
        width: 100%;
    }
    .chat-container {
        max-height: 500px;
        overflow-y: auto;
        padding: 10px;
        margin: 20px 0;
        border-radius: 10px;
        background-color: #0e1117;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🚀 AWS EC2 Docker Deployer")

# Check for API key
if "GITHUB_TOKEN" not in os.environ:
    st.warning(
        "⚠️ Please assign your OpenAI API key to 'GITHUB_TOKEN' variable inside .env file\n\n"
        "Then run 'docker compose up -d --build'"
    )
    st.stop()

st.info("""
**Before deploying, make sure you have done the following:**

* ✅ Create an **IAM User** in AWS and generate **Access Key** and **Secret Key** with full EC2 permissions.
* ✅ Create a **Key Pair** in AWS.
* ✅ Choose the **region** where this key pair exists and enter its **exact name** in the form.
""")

# Initialize session state
def init_session_state():
    """Initialize all session state variables"""
    defaults = {
        "request_id": None,
        "confirmed": False,
        "ai_result": None,
        "aws_access": "",
        "aws_secret": "",
        "deployment_status": None,  # None, 'deploying', 'success', 'failed'
        "deployment_complete": False,
        "error_message": None,
        "user_prompt": None,  # Store user's prompt for chat display
        "deployment_message": None  # Store deployment details message
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()


def display_chat_message(message: str, sender: str = "ai", show_label: bool = True):
    """Display a styled chat message"""
    if sender == "user":
        label = '<div style="text-align: right; font-size: 12px; color: #888; margin-bottom: 4px; font-weight: 500;">You</div>' if show_label else ''
        st.markdown(
            f"""
            {label}
            <div style="display: flex; justify-content: flex-end; margin: 10px 0;">
                <div style="
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 12px 16px;
                    border-radius: 18px 18px 4px 18px;
                    max-width: 70%;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    ">
                    {message}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:  # AI
        label = '<div style="text-align: left; font-size: 12px; color: #888; margin-bottom: 4px; font-weight: 500;">AI Agent</div>' if show_label else ''
        st.markdown(
            f"""
            {label}
            <div style="display: flex; justify-content: flex-start; margin: 10px 0;">
                <div style="
                    background-color: #2d2d2d;
                    color: #e0e0e0;
                    padding: 12px 16px;
                    border-radius: 18px 18px 18px 4px;
                    max-width: 70%;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    border: 1px solid #3d3d3d;
                    ">
                    {message}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def reset_session_state():
    """Reset session state to initial values"""
    st.session_state.request_id = None
    st.session_state.ai_result = None
    st.session_state.confirmed = False
    st.session_state.aws_access = ""
    st.session_state.aws_secret = ""
    st.session_state.deployment_status = None
    st.session_state.deployment_complete = False
    st.session_state.error_message = None
    st.session_state.user_prompt = None
    st.session_state.deployment_message = None


def make_api_request(method: str, endpoint: str, **kwargs) -> Optional[Dict[Any, Any]]:
    """Make API request with error handling"""
    try:
        url = f"{API_URL}{endpoint}"
        response = requests.request(method, url, timeout=30, **kwargs)
        
        if response.status_code != 200:
            try:
                error_data = response.json()
                error_msg = error_data.get("error", response.text)
            except ValueError:
                error_msg = response.text or f"HTTP {response.status_code} error"
            return {"error": error_msg, "status_code": response.status_code}
        
        return response.json()
    except requests.exceptions.Timeout:
        return {"error": "Request timed out. Please try again."}
    except requests.exceptions.ConnectionError:
        return {"error": f"Cannot connect to API at {API_URL}. Please check if the backend is running."}
    except Exception as e:
        return {"error": f"Unexpected error: {str(e)}"}


def submit_request(prompt: str):
    """Submit user request to API"""
    if not prompt.strip():
        st.warning("Please enter a prompt first.")
        return
    
    reset_session_state()
    st.session_state.user_prompt = prompt  # Save the user's prompt
    
    with st.spinner("Submitting your request..."):
        result = make_api_request("POST", "/request", json={"text": prompt})
        
        if result and "error" not in result:
            st.session_state.request_id = result.get("request_id")
            st.success(f"✅ Request submitted successfully! ID: {st.session_state.request_id}")
        else:
            st.error(f"❌ Error submitting request: {result.get('error', 'Unknown error')}")


def poll_ai_result(request_id: str) -> Optional[str]:
    """Poll for AI configuration result"""
    max_attempts = 60  # 60 seconds timeout
    attempt = 0
    
    placeholder = st.empty()
    
    while attempt < max_attempts:
        result = make_api_request("GET", f"/result/{request_id}")
        
        if result and "error" not in result:
            status = result.get("status")
            
            if status == "done":
                placeholder.success("✅ Configuration ready for review!")
                return result.get("result")
            else:
                placeholder.info(f"⏳ AI is processing... ({attempt + 1}s)")
        else:
            placeholder.error(f"❌ Error fetching result: {result.get('error', 'Unknown error')}")
            st.error("Please make sure you have configured OpenAI API key with 'GITHUB_TOKEN' environment variable")
            return None
        
        time.sleep(1)
        attempt += 1
    
    placeholder.error("⏱️ Timeout: AI processing took too long. Please try again.")
    return None


def deploy_ec2(request_id: str, aws_access: str, aws_secret: str):
    """Deploy EC2 instance and poll for completion"""
    payload = {
        "request_id": request_id,
        "aws_access_key": aws_access,
        "aws_secret_key": aws_secret,
    }
    
    st.session_state.deployment_status = "deploying"
    
    progress_placeholder = st.empty()
    status_placeholder = st.empty()
    
    # Step 1: Trigger deployment (call once)
    progress_placeholder.info("🚀 Initiating EC2 deployment...")
    result = make_api_request("POST", "/create-ec2", json=payload)
    
    if result and "error" in result:
        st.session_state.deployment_status = "failed"
        st.session_state.error_message = result.get("error")
        status_placeholder.error(f"❌ Deployment failed: {result.get('error')}")
        return
    
    # Step 2: Poll the result endpoint for status
    max_attempts = 150  # 5 minutes timeout (2 second intervals)
    attempt = 0
    
    while attempt < max_attempts:
        time.sleep(2)
        attempt += 1
        
        # Poll the /result endpoint to check deployment status
        status_result = make_api_request("GET", f"/result/{request_id}")
        
        if status_result and "error" not in status_result:
            status = status_result.get("status")
            
            if status in ("deploying", "in_progress", "processing"):
                progress_placeholder.info(f"⏳ EC2 is being created... ({attempt * 2}s elapsed)")
                continue
            
            elif status in ("done", "deployed"):
                st.session_state.deployment_status = "success"
                st.session_state.deployment_complete = True
                progress_placeholder.empty()
                status_placeholder.success("🎉 EC2 deployment completed successfully!")
                
                # Extract and format deployment details
                result_data = status_result.get("result", {})
                
                # Try to parse result if it's a JSON string
                if isinstance(result_data, str):
                    try:
                        result_data = json.loads(result_data)
                    except:
                        pass
                
                # Build deployment details message
                details_lines = ["<strong>✅ Deployment Successful!</strong><br><br>"]
                
                if isinstance(result_data, dict):
                    # Try different possible field names
                    instance_id = result_data.get("instance_id") or result_data.get("InstanceId") or result_data.get("id")
                    public_ip = result_data.get("public_ip") or result_data.get("PublicIp") or result_data.get("ip")
                    region = result_data.get("region") or result_data.get("Region")
                    instance_type = result_data.get("instance_type") or result_data.get("InstanceType")
                    
                    if instance_id:
                        details_lines.append(f"<strong>Instance ID:</strong> {instance_id}<br>")
                    if public_ip:
                        details_lines.append(f"<strong>Public IP:</strong> {public_ip}<br>")
                    if region:
                        details_lines.append(f"<strong>Region:</strong> {region}<br>")
                    if instance_type:
                        details_lines.append(f"<strong>Instance Type:</strong> {instance_type}<br>")
                    
                    # If no specific fields found, show the whole dict
                    if len(details_lines) == 1:
                        details_lines.append(f"<pre>{json.dumps(result_data, indent=2)}</pre>")
                else:
                    details_lines.append(f"{result_data}")
                
                deployment_message = "".join(details_lines)
                
                # Store the deployment message to display in chat
                st.session_state.deployment_message = deployment_message
                return
            
            elif status == "failed":
                st.session_state.deployment_status = "failed"
                
                # Try to extract error message from result
                result_data = status_result.get("result", "Unknown error occurred")
                if isinstance(result_data, str):
                    try:
                        parsed = json.loads(result_data)
                        error_msg = parsed.get("error", result_data)
                    except:
                        error_msg = result_data
                else:
                    error_msg = result_data.get("error", "Unknown error occurred")
                
                st.session_state.error_message = error_msg
                status_placeholder.error(f"❌ Deployment failed: {error_msg}")
                return
        else:
            # If we can't get status, keep trying
            progress_placeholder.info(f"⏳ Checking deployment status... ({attempt * 2}s elapsed)")
    
    # Timeout
    st.session_state.deployment_status = "failed"
    st.session_state.error_message = "Deployment timeout"
    status_placeholder.error("⏱️ Deployment timeout. Please check AWS console for instance status.")


# Main UI Flow
# Step 1: Prompt Input
prompt = st.text_input("Enter your request (e.g., 'Deploy nginx container on AWS')")

if st.button("Submit Request"):
    submit_request(prompt)

# Step 2: Poll for AI Result
if st.session_state.request_id and not st.session_state.ai_result and not st.session_state.confirmed:
    with st.spinner("Waiting for AI configuration..."):
        ai_result = poll_ai_result(st.session_state.request_id)
        if ai_result:
            st.session_state.ai_result = ai_result
            st.rerun()

# Step 3: Display AI Result and Confirm
if st.session_state.ai_result and not st.session_state.confirmed:
    st.subheader("💬 Configuration Chat")
    
    # Chat container
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    
    # Display user's prompt
    if st.session_state.user_prompt:
        display_chat_message(st.session_state.user_prompt, sender="user")
    
    # Display AI's response
    display_chat_message(st.session_state.ai_result, sender="ai")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirm Configuration", use_container_width=True):
            st.session_state.confirmed = True
            st.rerun()
    with col2:
        if st.button("🔄 Start Over", use_container_width=True):
            reset_session_state()
            st.rerun()

# Step 4: AWS Credentials and Deployment
if st.session_state.confirmed and not st.session_state.deployment_complete:
    # Keep the chat visible
    st.subheader("💬 Configuration Chat")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    if st.session_state.user_prompt:
        display_chat_message(st.session_state.user_prompt, sender="user")
    display_chat_message(st.session_state.ai_result, sender="ai")
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.subheader("🔐 Enter Your AWS Credentials")
    
    aws_access = st.text_input(
        "AWS Access Key ID", 
        type="password", 
        value=st.session_state.aws_access,
        key="aws_access_input"
    )
    aws_secret = st.text_input(
        "AWS Secret Access Key", 
        type="password", 
        value=st.session_state.aws_secret,
        key="aws_secret_input"
    )
    
    # Update session state
    st.session_state.aws_access = aws_access
    st.session_state.aws_secret = aws_secret
    
    if st.button("🚀 Deploy EC2 Instance", use_container_width=True):
        if not aws_access or not aws_secret:
            st.warning("⚠️ Please fill in both AWS credentials.")
        elif st.session_state.deployment_status == "deploying":
            st.info("⏳ Deployment already in progress...")
        else:
            with st.spinner("Deploying EC2 instance..."):
                deploy_ec2(st.session_state.request_id, aws_access, aws_secret)
    
    # Show "Start Over" button if deployment failed
    if st.session_state.deployment_status == "failed":
        st.markdown("---")
        if st.button("🔄 Start Over", use_container_width=True, key="start_over_after_error"):
            reset_session_state()
            st.rerun()

# Step 5: Show success message and option to deploy another
if st.session_state.deployment_complete:
    # Keep the chat visible
    st.subheader("💬 Configuration Chat")
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    if st.session_state.user_prompt:
        display_chat_message(st.session_state.user_prompt, sender="user")
    display_chat_message(st.session_state.ai_result, sender="ai", show_label=False)
    
    # Display deployment details as AI message
    if st.session_state.deployment_message:
        display_chat_message(st.session_state.deployment_message, sender="ai", show_label=False)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.balloons()
    
    if st.button("🆕 Deploy Another Instance", use_container_width=True):
        reset_session_state()
        st.rerun()