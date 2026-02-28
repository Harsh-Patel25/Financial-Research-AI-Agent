"""
Financial Analyst Agent (ai/analyst.py)

Responsible for taking structured market data (Price, Techs) and context (News)
and feeding it to the LLM (Gemini/OpenAI) with strict instructions to generate
a deterministic, professional JSON analysis.

Implements Task 5:
- strict system prompt
- low temperature
- validation via Pydantic output parsers

Implements Task 6:
- JSON validation retry (1 attempt) with correction prompt injection
- Toxicity / content safety moderation filter on every LLM output
"""

import json
import logging
from typing import Dict, Any, Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import ValidationError

from app.core.config import settings
from app.schemas.analysis import FinancialAnalysisResult
from app.schemas.stock import StockDataResponse
from app.schemas.news import NewsResponse
from app.ai.moderation import run_toxicity_check
from app.ai.hallucination_check import run_hallucination_check
from app.ai.response_limits import run_length_check

logger = logging.getLogger(__name__)


class AnalystAgent:
    """
    Wraps the LLM interaction logic. Disables creativity, enforces strict JSON shapes,
    and handles formatting context blocks.
    """

    def __init__(self):
        # Prefer Gemini if key exists, else fallback to OpenAI
        if settings.gemini_api_key:
            self.llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.2, # Very low temperature for maximum determinism
                api_key=settings.gemini_api_key
            )
        elif settings.openai_api_key:
            self.llm = ChatOpenAI(
                model="gpt-4o-mini",
                temperature=0.2,
                api_key=settings.openai_api_key
            )
        else:
            raise ValueError("No LLM API key configured (gemini_api_key or openai_api_key).")

        self.parser = PydanticOutputParser(pydantic_object=FinancialAnalysisResult)

        self.system_prompt = """
You are an elite, professional financial analyst. 
Your job is to read raw market data, technical indicators, and recent news headlines, then synthesize this into a structured, highly objective analysis.

CRITICAL RULES:
1. No creative language, no metaphors, no financial advice. Stick to facts and data.
2. If the data is missing (e.g. RSI is null), acknowledge it or skip it. Do not hallucinate values.
3. You MUST format your response EXACTLY following the schema below.
4. ONLY return a valid JSON object. Do not include markdown code blocks, pre-text, or post-text. 

## EXPECTED JSON OUTPUT FORMAT
{format_instructions}
"""

    def analyze_stock(
        self, 
        stock_data: StockDataResponse, 
        news_data: Optional[NewsResponse] = None
    ) -> FinancialAnalysisResult:
        """
        Injects the structured data into the prompt, triggers the LLM, and forces validation.
        """
        logger.info(f"Generating LLM analysis for {stock_data.symbol}")

        # 1. Format the Data
        stock_context = json.dumps(stock_data.model_dump(mode="json"), indent=2)
        
        news_context = "No recent news available."
        if news_data and news_data.count > 0:
            news_dump = [a.model_dump(mode="json") for a in news_data.articles]
            news_context = json.dumps(news_dump, indent=2)

        human_prompt = f"""
## TARGET SYMBOL: {stock_data.symbol}

### 1. RAW MARKET DATA & TECHNICALS
{stock_context}

### 2. RECENT NEWS CONTEXT
{news_context}

Synthesize this data immediately.
"""

        # 2. Build the Message List
        messages = [
            SystemMessage(content=self.system_prompt.replace(
                "{format_instructions}", 
                self.parser.get_format_instructions()
            )),
            HumanMessage(content=human_prompt)
        ]

        # 3. Call the LLM with a 1-retry guardrail
        max_retries = 1
        for attempt in range(max_retries + 1):
            try:
                response = self.llm.invoke(messages)
                raw_content = response.content

                # Attempt to strip ```json wrappers if the LLM leaked them despite instructions
                raw_content = raw_content.strip()
                if raw_content.startswith("```json"):
                    raw_content = raw_content[7:]
                if raw_content.endswith("```"):
                    raw_content = raw_content[:-3]
                raw_content = raw_content.strip()

                # 4. Defensive JSON Pre-parse — catch malformed JSON before Pydantic
                try:
                    json.loads(raw_content)  # dry-run parse — raises JSONDecodeError if invalid
                except json.JSONDecodeError as jde:
                    logger.warning(
                        "Attempt %d: Raw LLM response is not valid JSON for %s: %s",
                        attempt + 1, stock_data.symbol, str(jde)
                    )
                    # Treat as a ValidationError — triggers the retry / fallback path
                    raise ValidationError.from_exception_data(
                        title="JSONDecodeError",
                        line_errors=[{
                            "type": "json_invalid",
                            "loc": ("raw_content",),
                            "msg": f"LLM returned non-JSON content: {str(jde)}",
                            "input": raw_content[:200],
                            "ctx": {"error": str(jde)},
                        }],
                    ) from jde

                # 5. Pydantic Schema Validation
                result = self.parser.parse(raw_content)
                logger.info(f"LLM analysis completed successfully for {stock_data.symbol} on attempt {attempt + 1}")

                # --- Task 6: Toxicity / Content Safety Moderation ---
                result = run_toxicity_check(result)

                # --- Task 6: Hallucination Check (numeric cross-validation) ---
                result = run_hallucination_check(result, stock_data)

                # --- Task 6: Response Length Limits (trim oversized fields) ---
                result = run_length_check(result)

                return result

            except ValidationError as ve:
                logger.warning(f"Attempt {attempt + 1}: LLM returned invalid JSON schema for {stock_data.symbol}: {ve}")
                if attempt < max_retries:
                    logger.info(f"Retrying LLM analysis for {stock_data.symbol} with correction instruction...")
                    # Append the error and ask for a correction
                    correction_message = HumanMessage(
                        content=f"Your previous response failed validation with the following error:\n{ve}\n\n"
                                f"Please correct your JSON output and ensure it EXACTLY matches the requested schema."
                    )
                    messages.append(response) # Add the bad response to context
                    messages.append(correction_message)
                else:
                    logger.error(f"Final attempt failed for {stock_data.symbol}. Unable to retrieve valid JSON analysis.")
                    return FinancialAnalysisResult(
                        summary="Analysis failed due to repetitive validation errors from the AI model.",
                        sentiment="NEUTRAL",
                        key_findings=[],
                        risk_factors=["System encountered an unrecoverable validation error during synthesis."],
                        technical_posture="Data unavailable due to parsing failure."
                    )
            except Exception as exc:
                logger.error(f"LLM inference failed for {stock_data.symbol}: {exc}")
                raise RuntimeError(f"Failed to generate analysis: {exc}") from exc


# Module-level singleton to reuse the Langchain setup
analyst_agent = AnalystAgent()
