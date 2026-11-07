# Lingua AI — gradient edition

A Streamlit language translator with automatic language detection, voice input, browser speech playback, translation history, and a responsive gradient UI.

## Run locally (Windows PowerShell)

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip
py -m pip install -r requirements.txt
py -m streamlit run app.py
```

If PowerShell blocks activation, use this instead:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m streamlit run app.py
```

## Deploy to Streamlit Community Cloud

1. Create a GitHub repository for this project.
2. Upload `app.py`, `requirements.txt`, `.gitignore`, and `.streamlit/config.toml`.
3. Go to https://share.streamlit.io/ and sign in with GitHub.
4. Create an app, select your repository and branch, and set the main file to `app.py`.
5. Deploy. Test microphone permissions and speech playback on the public URL.

## Free translation providers — important limitations

- The app tries `GoogleTranslator` first and attempts `MyMemoryTranslator` as a fallback after provider request/rate-limit errors.
- Both are free/unofficial or community-accessible endpoints; availability, quotas, quality, and language coverage can change. Neither gives this student project a production SLA.
- Automatic language detection uses `langdetect`, which is heuristic and can be inaccurate for very short text, names, mixed-language text, or closely related languages.
- If a provider throttles requests, wait and retry later. Do not put retry loops around rate limits: they can make throttling worse.
- Do not use this free setup for confidential, legal, medical, or other high-stakes translations.

## Voice features

- Voice typing uses Streamlit's audio recording control and the SpeechRecognition package's Google web speech recognition backend. It needs microphone permission and internet access.
- For Auto detect voice typing currently defaults to English because speech recognition needs a language hint. Select the spoken language before recording for better recognition.
- Listen buttons use the visitor's browser speech synthesis. Available voices depend on the browser and operating system.

## Data and privacy

- Translation history is kept in Streamlit session state and is not a permanent database.
- Text is sent to external translation/speech services. Tell users this before collecting sensitive content.
- Do not add API keys or credentials to `app.py` or commit them to GitHub.
- A persistent multi-user product needs a database, privacy notice, abuse protection, and provider terms review.

## Files

- `app.py` — application
- `requirements.txt` — Python dependencies
- `.streamlit/config.toml` — theme configuration
- `.gitignore` — excludes local environment and secrets
