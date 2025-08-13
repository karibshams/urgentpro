import json
import time
import streamlit as st
from chatbot_setup import process_records_parallel, gpt_translate_text

st.set_page_config(page_title="Q/A Validator", layout="wide")
st.title("JSON Question-Answer Validator & Fixer")

# Initialize session state
for key in ["original_data", "processed_data", "processed_en_data", "last_uploaded_file"]:
    if key not in st.session_state:
        st.session_state[key] = None

uploaded = st.file_uploader("Upload JSON File", type="json")

# Only load data on NEW upload (check if it's a different file)
if uploaded and uploaded.name != st.session_state.get("last_uploaded_file"):
    st.session_state["original_data"] = json.load(uploaded)
    if isinstance(st.session_state["original_data"], dict):
        st.session_state["original_data"] = [st.session_state["original_data"]]
    # Reset processed data only on new upload
    st.session_state["processed_data"] = None
    st.session_state["processed_en_data"] = None
    st.session_state["last_uploaded_file"] = uploaded.name

# Show original data
if st.session_state["original_data"]:
    st.subheader("Original Data")
    st.json(st.session_state["original_data"])

# Processing
if st.button("Start Processing"):
    # Only process if not already processed
    if not st.session_state["processed_data"]:
        start_time = time.time()
        total = len(st.session_state["original_data"])
        progress_bar = st.progress(0)
        status_text = st.empty()

        processed = []
        batch_size = 5
        for i in range(0, total, batch_size):
            batch = st.session_state["original_data"][i:i+batch_size]
            batch_results = process_records_parallel(batch, max_workers=batch_size)
            processed.extend(batch_results)
            progress_bar.progress(min(100, int((len(processed)/total)*100)))
            status_text.text(f"Processed {len(processed)} of {total} records...")

        elapsed = time.time() - start_time
        st.session_state["processed_data"] = processed

        # Translate to English
        processed_en = [gpt_translate_text(rec, "English") for rec in processed]
        st.session_state["processed_en_data"] = processed_en

# Show processed data if exists
if st.session_state["processed_data"]:
    st.subheader("Processed Data")
    st.json(st.session_state["processed_data"])

    # Summary
    processed = st.session_state["processed_data"]
    valid = sum(1 for r in processed if r.get("_validation", {}).get("valid") is True)
    corrected = sum(1 for r in processed if r.get("_validation", {}).get("corrected") is True)
    failed = sum(1 for r in processed if not r.get("_validation", {}).get("valid", False) and not r.get("_validation", {}).get("corrected", False))
    
    st.subheader("Summary")
    st.write(f"Total records: {len(processed)}")
    st.write(f"Valid (no changes): {valid}")
    st.write(f"Corrected by AI: {corrected}")
    st.write(f"Failed to correct/flagged: {failed}")

    # Download buttons (outside processing button)
    st.download_button(
        "Download Corrected JSON (Original Language)",
        data=json.dumps(st.session_state["processed_data"], indent=2, ensure_ascii=False),
        file_name="corrected.json",
        mime="application/json"
    )

    st.download_button(
        "Download Corrected JSON (English)",
        data=json.dumps(st.session_state["processed_en_data"], indent=2, ensure_ascii=False),
        file_name="corrected_en.json",
        mime="application/json"
    )