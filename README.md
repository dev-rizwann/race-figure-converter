# Race Figure Converter

Streamlit app that converts racing PDFs into a single Excel workbook.

The output lists each race as a compact table with:

- Runner
- Weight lbs
- Last Speed
- Figure = Weight lbs - Last Speed

Rows are sorted lowest figure first within each race.

The app accepts up to 10 PDFs at once. Each PDF gets its own output sheet in
the workbook, plus a Source Audit sheet with the raw parsed source lines for
checking accuracy.

## Run locally

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py
```

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub.
2. In Streamlit Community Cloud, choose **New app**.
3. Select this repository.
4. Set main file path to `streamlit_app.py`.
5. Open **Advanced settings**.
6. Set Python version to **3.12**.
7. Leave **Secrets** blank. This app does not use API keys or environment variables.
8. Deploy.

If you already deployed the app with a different Python version, delete the app in
Streamlit Cloud and redeploy it. Streamlit Cloud does not change Python versions
in place after the app has been created.
