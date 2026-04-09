import os
import sys
import json

from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

# Absolute imports natively from the workspace root (IDE resolves this statically)
from backend.app.ai.analyst import analyst_agent
from backend.app.schemas.stock import StockDataResponse
from backend.app.schemas.news import NewsResponse

# Golden Dataset: Input Data -> Expected Context
EVAL_DATASET = [
    {
        "symbol": "AAPL",
        "mock_stock": StockDataResponse(
            symbol="AAPL", current_price=180.50, previous_close=175.0, 
            day_high=181.0, day_low=174.0, volume=5000000, currency="USD",
            rsi=85.5, sma=170.0, ema=172.0
        ),
        "expected_sentiment": "BULLISH",
        "rationale": "High RSI and price above SMA/EMA."
    },
    {
        "symbol": "TSLA",
        "mock_stock": StockDataResponse(
            symbol="TSLA", current_price=150.00, previous_close=160.0, 
            day_high=162.0, day_low=149.0, volume=8000000, currency="USD",
            rsi=25.0, sma=180.0, ema=175.0
        ),
        "expected_sentiment": "BEARISH",
        "rationale": "Price cratered below moving averages, RSI is oversold."
    }
]

JUDGE_PROMPT = """
You are an AI grader evaluating a financial AI agent.
The agent was given specific market data.
It produced the following JSON response:
{actual_response}

The expected general sentiment was: {expected_sentiment}.

Score the agent from 0.0 to 1.0 based on whether it correctly identified the sentiment and whether it hallucinated any data.
Only return a JSON dictionary with keys 'score' (float) and 'reason' (string). No other text.
"""

def run_evaluation():
    print("🚀 Starting LLM-as-a-Judge Evaluation...")
    judge_llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
    prompt = PromptTemplate.from_template(JUDGE_PROMPT)
    
    total_score = 0.0
    
    for i, data in enumerate(EVAL_DATASET):
        print(f"\nEvaluating Dataset {i+1}: {data['symbol']}")
        # 1. Run the system
        result = analyst_agent.analyze_stock(data["mock_stock"], news_data=None)
        
        # 2. Judge the result
        judge_chain = prompt | judge_llm
        eval_result = judge_chain.invoke({
            "actual_response": result.model_dump_json(),
            "expected_sentiment": data["expected_sentiment"]
        })
        
        try:
            score_data = json.loads(eval_result.content.strip("```json\n"))
            score = score_data.get("score", 0.0)
            total_score += score
            print(f"Status: {'✅ Pass' if score > 0.8 else '❌ Fail'} (Score: {score})")
            print(f"Reason: {score_data.get('reason')}")
        except Exception as e:
            print(f"Failed to parse judge output: {e}\nOutput: {eval_result.content}")
            
    avg_score = total_score / len(EVAL_DATASET)
    print(f"\n📊 Final Average Score: {avg_score * 100:.1f}%")
    if avg_score >= 0.85:
        print("🎉 System passed the production readiness threshold!")
    else:
        print("⚠️ System needs tuning before production.")

if __name__ == "__main__":
    run_evaluation()
