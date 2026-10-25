# 🏗️ Multimodal Construction Intelligence Platform

Skill Wallet Capstone Project 1 (Generative AI | Real Estate Decision Support)

An AI decision-support app that analyses construction site photos and plans projects, built with Streamlit and Google Gemini.

## Features

| Module | What it does |
|---|---|
| 🦺 Safety & PPE Audit | Upload a site photo, get a safety score, PPE checklist (helmet, vest, boots, harness), hazards with severity and remedies, and a downloadable JSON report |
| 🧱 Crack Diagnostics | Classifies defects (Hairline, Settlement, Structural Shear, Thermal Expansion, Spalling) with width, root causes, repairs and urgency |
| 📐 Planning & Valuation | Budget, CapEx, asset value in INR (Lakhs/Crores), steel and cement needs, milestone tracker, AI concept render |
| 🌦️ Site Assistant | Weather-aware safety protocols and a multi-turn engineering chatbot |

No API key? The app runs in **demo mode** with sample outputs.

## Tech Stack

Python 3.9+, Streamlit, Google Gemini (`google-genai`), Pillow, Pollinations AI, JSON data contracts.

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Paste your Gemini API key (free from [aistudio.google.com](https://aistudio.google.com)) in the sidebar.

## Deploy on Streamlit Community Cloud

1. Push this repo to GitHub (public).
2. Go to [share.streamlit.io](https://share.streamlit.io) and click **New app**.
3. Select the repo, branch `main`, main file `app.py`, then **Deploy**.

## Project Structure

```
├── app.py
├── requirements.txt
└── README.md
```

## Disclaimer

Cost and valuation figures are indicative estimates. AI safety and structural findings must be verified by a qualified engineer or safety officer.
