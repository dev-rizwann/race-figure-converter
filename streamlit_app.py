from __future__ import annotations

import streamlit as st

from race_parser import parse_pdf
from workbook_builder import build_workbook, output_filename, sorted_runners


st.set_page_config(page_title="Race Figure Converter", page_icon="🏇", layout="wide")

st.title("Race Figure Converter")

uploaded = st.file_uploader("Upload racing PDF", type=["pdf"])


@st.cache_data(show_spinner=False)
def _process(file_bytes: bytes, name: str):
    parsed = parse_pdf(file_bytes, name)
    excel_bytes = build_workbook(parsed) if parsed.races else b""
    return parsed, excel_bytes


def render_light_preview(parsed) -> None:
    st.subheader("Detected races")
    for race in parsed.races:
        runners = sorted_runners(race.runners)
        best = next((runner for runner in runners if runner.figure is not None), None)
        if best:
            st.write(f"{race.label}: {len(runners)} runners. Lowest: {best.name} ({best.figure}).")
        else:
            st.write(f"{race.label}: {len(runners)} runners. No usable last speed figures found.")


if uploaded:
    with st.spinner("Reading PDF and creating Excel..."):
        try:
            parsed, excel_bytes = _process(uploaded.getvalue(), uploaded.name)
        except Exception as exc:
            st.error(f"Could not process this PDF: {exc}")
            st.stop()

    if not parsed.races:
        st.error("No races were found in this PDF.")
        for warning in parsed.warnings:
            st.warning(warning)
        st.stop()

    total_runners = sum(len(race.runners) for race in parsed.races)
    blank_figures = sum(
        1
        for race in parsed.races
        for runner in race.runners
        if runner.last_speed_figure is None
    )

    st.success(f"Found {len(parsed.races)} races and {total_runners} runners.")

    st.download_button(
        "Download Excel",
        data=excel_bytes,
        file_name=output_filename(uploaded.name),
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )

    if blank_figures:
        st.warning(f"{blank_figures} runner(s) had no usable last speed figure, so their figure is blank.")

    render_light_preview(parsed)
else:
    st.info("Upload a race PDF to create the one-sheet Excel output.")
