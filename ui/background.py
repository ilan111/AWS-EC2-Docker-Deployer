import base64
import streamlit as st

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