import json
import time
import streamlit as st
from chatbot_setup import process_records_parallel

st.set_page_config(page_title="Q/A Validator", layout="wide")
st.title("✅ JSON Question-Answer Validator & Fixer")

uploaded = st.file_uploader("Upload JSON File", type="json")

if uploaded:
    raw_data = json.load(uploaded)
    if isinstance(raw_data, dict):
        raw_data = [raw_data]

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Original Data")
        st.json(raw_data)

    if st.button("Start Processing"):
        start_time = time.time()
        total = len(raw_data)
        progress_bar = st.progress(0)
        status_text = st.empty()

        processed = []
        batch_size = 5

        for i in range(0, total, batch_size):
            batch = raw_data[i:i+batch_size]
            batch_results = process_records_parallel(batch, max_workers=batch_size)
            processed.extend(batch_results)
            progress_bar.progress(min(100, int((len(processed) / total) * 100)))
            status_text.text(f"Processed {len(processed)} of {total} records...")

        elapsed = time.time() - start_time

        with col2:
            st.subheader("Processed Data")
            st.json(processed)

        valid = sum(1 for r in processed if r.get("_validation", {}).get("valid") is True)
        corrected = sum(1 for r in processed if r.get("_validation", {}).get("corrected") is True)
        failed = sum(1 for r in processed if not r.get("_validation", {}).get("valid", False) and not r.get("_validation", {}).get("corrected", False))

        st.subheader("Summary")
        st.write(f"Total records: {total}")
        st.write(f"Valid (no changes): {valid}")
        st.write(f"Corrected by AI: {corrected}")
        st.write(f"Failed to correct/flagged: {failed}")
        st.write(f"Elapsed time: {elapsed:.2f} seconds")

        st.download_button(
            "Download Corrected JSON",
            data=json.dumps(processed, indent=2, ensure_ascii=False),
            file_name="corrected.json",
            mime="application/json"
        )
