# Financial Research AI Agent

An AI-powered financial research assistant that aggregates market data, performs sentiment analysis, and provides portfolio insights.

## Project Structure

```
financial_ai/
│
├── app/
│   ├── ai/             # AI logic & agent implementation
│   ├── data/           # Data fetching modules (APIs)
│   ├── portfolio/      # Portfolio management logic
│   ├── sentiment/      # Sentiment analysis models
│   ├── main.py         # FastAPI backend entry point
│
├── frontend/
│   └── streamlit_app.py # Streamlit dashboard
│
├── .env.example        # Template for environment variables
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

## Setup Instructions

1.  **Clone the repository:**
    ```bash
    git clone <repository-url>
    cd financial_ai
    ```

2.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use: venv\Scripts\activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure Environment Variables:**
    - Copy `.env.example` to `.env`:
        ```bash
        cp .env.example .env
        ```
    - Open `.env` and add your API keys (Alpha Vantage, NewsAPI, etc.).

5.  **Run the Application:**
    - **Backend (FastAPI):**
        ```bash
        uvicorn app.main:app --reload
        ```
    - **Frontend (Streamlit):**
        ```bash
        streamlit run frontend/streamlit_app.py
        ```

## Features
- **Market Data Retrieval:** Real-time stock, crypto, and economic data.
- **Sentiment Analysis:** Analyzes news and social media sentiment.
- **AI Integration:** Uses LLMs for financial insights.

## License
MIT
