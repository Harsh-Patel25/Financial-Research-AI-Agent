# 🚀 Deployment Guide: Streamlit Community Cloud

Your Financial Research AI Agent is fully prepared for a 1-click deployment on Streamlit Community Cloud. This platform is free and hooks directly into your GitHub repository.

## Step 1: Push to GitHub
Ensure all your files are pushed to a public or private GitHub repository.
```bash
git add .
git commit -m "Ready for Streamlit Cloud deployment"
git push origin main
```

## Step 2: Connect Streamlit
1. Go to [share.streamlit.io](https://share.streamlit.io/).
2. Log in with your GitHub account.
3. Click **"New app"**.
4. Fill in the following details:
   - **Repository**: Select your GitHub repository.
   - **Branch**: `main`
   - **Main file path**: `frontend/streamlit_app.py` 

*Note: You must point to the frontend folder, not the root!*

## Step 3: Add API Keys (Secrets)
Because your `.env` file is (correctly) ignored by `.gitignore`, Streamlit Cloud won't have your API keys by default.
1. Before you click "Deploy", click on **"Advanced settings"**.
2. A text box for **Secrets** will appear.
3. Paste your API keys exactly like your local `.env` file:
```toml
# Streamlit Secrets format (TOML)
GEMINI_API_KEY="your-gemini-key-here"
OPENAI_API_KEY="your-openai-key-here"
```
*(You only need to provide either Gemini OR OpenAI, just like local development).*

## Step 4: Deploy!
Click **"Deploy!"**. 
- Streamlit will read your `requirements.txt` and automatically install FastAPI, LangChain, yFinance, etc.
- It will boot up the Python environment and launch your dashboard.
- You will get a shareable URL (e.g., `https://your-financial-agent.streamlit.app`).

---

# 🎥 Final Step: Record your Demo
Once your app is live on its `streamlit.app` URL:
1. Open Loom or OBS.
2. Start recording.
3. Type `RELIANCE.NS` in the input box and hit Enter.
4. Show the loading bars and let the audience watch the live Price, Chart, and News populate.
5. Show the AI Analyst typing out its fundamental analysis based on the live data.
6. Stop the recording. 

**Congratulations! Track A is 100% complete.**
