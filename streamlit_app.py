import streamlit as st

st.set_page_config(
    page_title="Prescription Explorer",
    page_icon="💊",
    layout="wide"
)

st.title("💊 Prescription Data Explorer")
st.markdown("""
Use the sidebar (▸) to navigate between pages:

- **Overview**  
- **By Medication**  
- **By Generic**  
- **Brand vs Generic**
""")
