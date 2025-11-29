import base64
import streamlit as st
import os
from PIL import Image

def add_responsive_bg(image_file):
    with open(image_file, "rb") as f:
        data = f.read()
    encoded = base64.b64encode(data).decode()

    st.markdown(
        f"""
        <style>

        /* Make entire page stretch correctly */
        html, body {{
            height: 100%;
            margin: 0;
            padding: 0;
        }}

        /* Background image on the main container */
        .stApp {{
            background: url("data:image/png;base64,{encoded}") center/cover no-repeat fixed;
            position: relative;
            min-height: 100vh;
        }}

        /* DARK overlay */
        .stApp::before {{
            content: "";
            position: fixed;     /* FIXED solves the mobile disappearing issue */
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.55);
            z-index: -1;          /* overlay under the app always */
        }}

        /* Push everything above the overlay */
        .stApp, .block-container, .main, .stMarkdown, .stButton, .stTextInput {{
            position: relative !important;
            z-index: 1 !important;
        }}

        /* Mobile background crop fix */
        @media (max-width: 600px) {{
            .stApp {{
                background-position: center;
                background-attachment: scroll;  /* mobile-safe */
            }}
        }}
        </style>
        """,
        unsafe_allow_html=True
    )

def add_logo(logo_path: str, width: int = 200):
    """Place a centered logo with real, enforced width (works regardless of Streamlit quirks)."""

    # Load file
    with open(logo_path, "rb") as f:
        logo_bytes = f.read()
    logo_base64 = base64.b64encode(logo_bytes).decode()

    # CSS + HTML injected directly in absolute layer
    html = f"""
    <style>
        .logo-container {{
            display: flex;
            justify-content: center;
            width: 100%;
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        .logo-img {{
            width: {width}px !important;
            max-width: {width}px !important;
            height: auto !important;
        }}
    </style>

    <div class="logo-container">
        <img class="logo-img" src="data:image/png;base64,{logo_base64}">
    </div>
    """

    st.markdown(html, unsafe_allow_html=True)


def img_to_base64(img):
    """Convert PIL image to base64 string."""
    from io import BytesIO
    buf = BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")