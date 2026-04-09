"""
Financial Analyst Agent (ai/analyst.py) - LangGraph Edition

Responsible for taking structured market data (Price, Techs) and context (News)
and feeding it to the LLM (Gemini/OpenAI) with strict instructions to generate
a deterministic, professional JSON analysis.

Now powered by LangGraph to handle stateful, multi-node cyclic workflows:
[START] -> [Generate] -> [Validate & Guardrails] -> (Retry Loop) -> [END]
"""

import json
import logging
import time
from typing import Dict, Any, Optional, TypedDict, Annotated

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from pydantic import ValidationError

from ..core.config import settings
from ..schemas.analysis import FinancialAnalysisResult
from ..schemas.stock import StockDataResponse
from ..schemas.news import NewsResponse
from .scoring import compute_technical_signals
from .moderation import run_toxicity_check
from .hallucination_check import run_hallucination_check
from .response_limits import run_length_check

# Logger must be defined BEFORE the vader import try/except block
# so it can be used in the except clause.
logger = logging.getLogger(__name__)

# VADER — fast deterministic NLP sentiment (no API call, no rate limit)
try:
    from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
    _vader = SentimentIntensityAnalyzer()
except ImportError:
    _vader = None
    logging.warning("vaderSentiment not installed. Falling back to LLM-only sentiment.")


def _score_headlines_with_vader(news_data: Optional["NewsResponse"]) -> dict:
    """Runs VADER on all article titles — returns aggregate compound score & category."""
    if not _vader or not news_data or news_data.count == 0:
        return {"score": 0.0, "label": "NEUTRAL", "headlines_scored": 0}
    
    scores = []
    for article in news_data.articles[:8]:  # Max 8 headlines
        if article.title:
            vs = _vader.polarity_scores(article.title)
            scores.append(vs["compound"])
    
    if not scores:
        return {"score": 0.0, "label": "NEUTRAL", "headlines_scored": 0}
    
    avg_score = sum(scores) / len(scores)
    label = "BULLISH" if avg_score >= 0.05 else "BEARISH" if avg_score <= -0.05 else "NEUTRAL"
    return {"score": round(avg_score, 3), "label": label, "headlines_scored": len(scores)}

# logger is already defined above (before vader import block)


# ── LangGraph State Definition ────────────────────────────────────────────────

class AgentState(TypedDict):
    """The graph state across nodes."""
    stock_data: StockDataResponse
    news_data: Optional[NewsResponse]
    messages: Annotated[list[BaseMessage], add_messages]
    parsed_result: Optional[FinancialAnalysisResult]
    retry_count: int


# ── Analyst Agent (LangGraph Wrapper) ─────────────────────────────────────────

class AnalystAgent:
    """
    Wraps the LangGraph setup and exposes a simple analyze_stock() 
    method to keep the rest of the application unchanged.
    """

    def __init__(self):
        # Priority: Groq (free, fast) → OpenAI → Gemini
        if settings.groq_api_key:
            self.llm = ChatGroq(
                model="llama-3.3-70b-versatile",
                temperature=0.2,
                api_key=settings.groq_api_key
            )
            logger.info("LLM initialized: Groq / llama-3.3-70b-versatile")
        elif settings.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                api_key=settings.openai_api_key
            )
            logger.info("LLM initialized: OpenAI / gpt-4o-mini")
        elif settings.gemini_api_key:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-pro",
                temperature=0.2,
                api_key=settings.gemini_api_key
            )
            logger.info("LLM initialized: Gemini / gemini-2.5-pro")
        else:
            raise ValueError("No LLM API key found. Set GROQ_API_KEY, OPENAI_API_KEY, or GEMINI_API_KEY in .env")

        self.parser = PydanticOutputParser(pydantic_object=FinancialAnalysisResult)

        self.system_prompt = """
You are the elite final Synthesis Node in a Financial Decision Intelligence System.
Your job is to read PRE-CALCULATED deterministic data (Moving Averages, RSI momentum, and NLP Sentiment) and synthesize this into a structured, highly professional analysis narrative.

CRITICAL RULES:
1. DO NOT GUESS TRENDS: You will be provided exact numerical technical momentum scores (Calculated by pandas/NumPy). You must base your technical interpretation on THESE numbers.
2. READ THE HEADLINES: Evaluate the provided news context and isolate the overarching market sentiment. Be ruthless. Assign a numerical value representation in your mind.
3. CONSTRUCT A CONFIDENCE SCORE: Based on how strongly the Technical Score aligns with the News Sentiment, assign a Confidence percentage out of 100%. (e.g. If RSI is oversold but SMA is death cross and news is terrible, confidence in a specific bounce might be low).
4. No creative language, no metaphors, no financial advice. Stick to facts and data.
5. You MUST format your response EXACTLY following the schema below.
6. ONLY return a valid JSON object. Do not include markdown code blocks, pre-text, or post-text. 

## EXPECTED JSON OUTPUT FORMAT
{format_instructions}
"""
        # Compile the LangGraph
        self._graph = self._build_graph()

    def _build_graph(self):
        """Constructs the iterative StateGraph for the analysis pipeline."""
        workflow = StateGraph(AgentState)

        workflow.add_node("generate_analysis", self._node_generate_analysis)
        workflow.add_node("validate_and_guard", self._node_validate_and_guard)
        workflow.add_node("fallback_analysis", self._node_fallback_analysis)

        workflow.add_edge(START, "generate_analysis")
        workflow.add_edge("generate_analysis", "validate_and_guard")
        
        # Conditional logic based on validation result
        workflow.add_conditional_edges(
            "validate_and_guard",
            self._edge_should_retry,
            {
                "end": END,
                "retry": "generate_analysis",
                "fallback": "fallback_analysis"
            }
        )
        workflow.add_edge("fallback_analysis", END)

        return workflow.compile()

    # ── Graph Nodes ───────────────────────────────────────────────────────────

    def _node_generate_analysis(self, state: AgentState) -> dict:
        """Node 1: Calls the LLM with rate-limit retry handling."""
        attempt = state['retry_count'] + 1
        logger.info(f"Node [Generate]: Invoking LLM for {state['stock_data'].symbol} (Attempt {attempt})")
        
        max_llm_retries = 3
        for llm_attempt in range(max_llm_retries):
            try:
                response = self.llm.invoke(state["messages"])
                return {"messages": [response]}
            except Exception as exc:
                exc_str = str(exc).lower()
                # Handle rate limit (429 / ResourceExhausted)
                if any(kw in exc_str for kw in ["429", "resource_exhausted", "quota", "retrydelay"]):
                    wait_secs = 60
                    logger.warning(
                        f"Rate limit hit for {state['stock_data'].symbol}. "
                        f"Waiting {wait_secs}s before retry {llm_attempt + 1}/{max_llm_retries}..."
                    )
                    time.sleep(wait_secs)
                else:
                    raise  # Non-rate-limit errors propagate immediately
        
        # If all retries exhausted raise the last error
        raise RuntimeError(f"LLM rate limit exceeded after {max_llm_retries} retries for {state['stock_data'].symbol}.")

    def _node_validate_and_guard(self, state: AgentState) -> dict:
        """Node 2: Defensive parse, Pydantic validation, Toxicity, Hallucination, & Length limits."""
        logger.info(f"Node [Validate]: Running validation pipeline for {state['stock_data'].symbol}")
        
        # The last message is the AI's response
        ai_response = state["messages"][-1].content
        raw_content = ai_response.strip()

        # 1. Strip markdown wrappers
        if raw_content.startswith("```json"):
            raw_content = raw_content[7:]
        if raw_content.endswith("```"):
            raw_content = raw_content[:-3]
        raw_content = raw_content.strip()

        try:
            # 2. Defensive JSON Pre-parse
            json.loads(raw_content)

            # 3. Pydantic validation
            result = self.parser.parse(raw_content)

            # 4. Content Guardrails Pipeline (Task 6)
            result = run_toxicity_check(result)
            result = run_hallucination_check(result, state["stock_data"])
            result = run_length_check(result)

            logger.info("Node [Validate]: Success. Moving to END.")
            return {"parsed_result": result}

        # Catch both json loads error and pydantic parse errors
        except Exception as ve:
            logger.warning(f"Node [Validate]: Failed - {ve}")
            
            # Format correction prompt to append to the conversation history
            correction_msg = HumanMessage(
                content=f"Your previous response failed validation with the following error:\n{ve}\n\n"
                        f"Please correct your JSON output and ensure it EXACTLY matches the requested schema without markdown blocks."
            )
            return {
                "messages": [correction_msg],
                "retry_count": state["retry_count"] + 1
            }

    def _node_fallback_analysis(self, state: AgentState) -> dict:
        """Node 3: Hardcoded fallback if the retry loop exhausts."""
        logger.error(f"Node [Fallback]: Max retries exhausted for {state['stock_data'].symbol}.")
        fallback = FinancialAnalysisResult(
            verdict="NEUTRAL",
            confidence=0,
            reasoning_summary="Analysis could not be completed due to repeated AI model validation errors. Please try again.",
            technical_signals=[],
            sentiment_signals=[],
            risk_assessment="System encountered an unrecoverable validation error during synthesis. Data quality may be insufficient.",
        )
        return {"parsed_result": fallback}

    # ── Graph Edges ───────────────────────────────────────────────────────────

    def _edge_should_retry(self, state: AgentState) -> str:
        """Determines next node post-validation."""
        if state.get("parsed_result") is not None:
            return "end" # Validation passed
        if state["retry_count"] < 1:  # Max 1 retry
            return "retry"
        return "fallback"

    # ── Main Entrypoint (Backward Compatible) ─────────────────────────────────

    def analyze_stock(
        self, 
        stock_data: StockDataResponse, 
        news_data: Optional[NewsResponse] = None,
        extracted_context: Optional[str] = None
    ) -> FinancialAnalysisResult:
        """
        Public API backward compatible with the older static script.
        Initializes graph state and runs the workflow.
        """
        logger.info(f"Initializing LangGraph analysis for {stock_data.symbol}")

        # 1. Pre-calculate Deterministic Intelligence
        tech_scores = compute_technical_signals(stock_data)
        
        # 2. VADER NLP pre-scoring (deterministic, no API call)
        vader_sentiment = _score_headlines_with_vader(news_data)
        
        # 3. Format Data Context for LLM Synthesis
        news_context = "No recent news available."
        
        if news_data and news_data.count > 0:
            news_dump = [a.model_dump(mode="json") for a in news_data.articles]
            news_context = json.dumps(news_dump, indent=2)

        rag_context = ""
        if extracted_context:
            rag_context = f"\n### 4. RELEVANT HYBRID CONTEXT\n{extracted_context}\n"

        human_prompt = f"""
## TARGET SYMBOL: {stock_data.symbol} | ALGO PRICE: {stock_data.current_price}

### 1. PRE-CALCULATED DETERMINISTIC TECHNICAL SIGNALS
- OVERALL MOMENTUM SCORE (Python Engine): {tech_scores['score']} / 1.0 (Signal: {tech_scores['momentum_signal']})
- CURRENT RSI (14-period): {tech_scores['rsi']}
- 50-Day Moving Average: {tech_scores['sma_50']}
- 200-Day Moving Average: {tech_scores['sma_200']}

### 2. VADER NEWS SENTIMENT (Deterministic NLP — DO NOT RECALCULATE)
- Compound Score: {vader_sentiment['score']} (range -1.0 to +1.0)
- Label: {vader_sentiment['label']}
- Headlines Analyzed: {vader_sentiment['headlines_scored']}

### 3. RAW NEWS HEADLINES (Reference only)
{news_context}
{rag_context}
Synthesize the pre-computed data above and emit the final Decision JSON immediately.
"""
        initial_messages = [
            SystemMessage(content=self.system_prompt.replace(
                "{format_instructions}", 
                self.parser.get_format_instructions()
            )),
            HumanMessage(content=human_prompt)
        ]

        # 2. Setup Initial State
        initial_state: AgentState = {
            "stock_data": stock_data,
            "news_data": news_data,
            "messages": initial_messages,
            "parsed_result": None,
            "retry_count": 0
        }

        # 3. Execute LangGraph
        config = {"recursion_limit": 10} # Prevent infinite loops
        final_state = self._graph.invoke(initial_state, config=config)

        # 4. Return the parsed Pydantic object
        return final_state["parsed_result"]


# Module-level singleton to reuse the Langchain setup
analyst_agent = AnalystAgent()
