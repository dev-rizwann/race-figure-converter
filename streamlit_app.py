from __future__ import annotations

import streamlit as st

from race_parser import parse_pdf
from workbook_builder import build_combined_workbook, combined_output_filename, sorted_runners


MAX_UPLOADS = 10
MAX_FILE_MB = 10
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


st.set_page_config(page_title="Race Figure Converter", layout="wide")

st.title("Race Figure Converter")

uploaded_files = st.file_uploader(
    "Upload racing PDFs",
    type=["pdf"],
    accept_multiple_files=True,
    help=f"Upload up to {MAX_UPLOADS} PDFs, max {MAX_FILE_MB} MB each. The app returns one Excel workbook.",
)


@st.cache_data(show_spinner=False)
def _process(files_payload: tuple[tuple[str, bytes], ...]):
    parsed_files = [parse_pdf(file_bytes, name) for name, file_bytes in files_payload]
    excel_bytes = build_combined_workbook(parsed_files) if parsed_files else b""
    return parsed_files, excel_bytes


def render_light_preview(parsed) -> None:
    for race in parsed.races:
        runners = sorted_runners(race.runners)
        best = next((runner for runner in runners if runner.figure is not None), None)
        if best:
            st.write(f"{race.label}: {len(runners)} runners. Lowest: {best.name} ({best.figure}).")
        else:
            st.write(f"{race.label}: {len(runners)} runners. No usable last speed figures found.")


if uploaded_files:
    if len(uploaded_files) > MAX_UPLOADS:
        st.error(f"Please upload {MAX_UPLOADS} PDFs or fewer.")
        st.stop()

    payload = tuple((uploaded.name, uploaded.getvalue()) for uploaded in uploaded_files)
    oversized = [name for name, file_bytes in payload if len(file_bytes) > MAX_FILE_BYTES]
    if oversized:
        st.error(f"Please keep each PDF under {MAX_FILE_MB} MB. Too large: {', '.join(oversized)}")
        st.stop()

    with st.spinner("Reading PDF files and creating Excel..."):
        try:
            parsed_files, excel_bytes = _process(payload)
        except Exception as exc:
            st.error(f"Could not process these PDF files: {exc}")
            st.stop()

    empty_files = [parsed.source_name for parsed in parsed_files if not parsed.races]
    if empty_files:
        st.error("No races were found in: " + ", ".join(empty_files))
        for parsed in parsed_files:
            for warning in parsed.warnings:
                st.warning(f"{parsed.source_name}: {warning}")
        st.stop()

    total_races = sum(len(parsed.races) for parsed in parsed_files)
    total_runners = sum(len(race.runners) for parsed in parsed_files for race in parsed.races)
    blank_figures = sum(
        1
        for parsed in parsed_files
        for race in parsed.races
        for runner in race.runners
        if runner.last_speed_figure is None
    )

    st.success(f"Found {total_races} races and {total_runners} runners across {len(parsed_files)} PDF file(s).")

    st.download_button(
        "Download Excel",
        data=excel_bytes,
        file_name=combined_output_filename([parsed.source_name for parsed in parsed_files]),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    if blank_figures:
        st.warning(f"{blank_figures} runner(s) had no usable last speed figure, so their figure is blank.")

    st.subheader("Detected races")
    for parsed in parsed_files:
        st.markdown(f"**{parsed.source_name}**")
        render_light_preview(parsed)
else:
    st.info("Upload up to 10 race PDFs to create one Excel output.")
