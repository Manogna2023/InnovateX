import streamlit as st
import requests

st.title("GigShield AI")

BASE_URL = "http://localhost:8000"  # we’ll change later

st.header("Health Check")

if st.button("Check API"):
    try:
        res = requests.get(f"{BASE_URL}/health")
        st.success(res.json())
    except:
        st.error("API not reachable")
