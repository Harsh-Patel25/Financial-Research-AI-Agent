from fpdf import FPDF
import re


def _safe(text: str) -> str:
    """Strips characters outside Latin-1 (emoji, CJK, etc.) so Helvetica never crashes."""
    if not text:
        return ""
    # Replace common emoji bullet stand-ins with plain ASCII
    text = text.replace("⚡", "[!]").replace("🔔", "[ALERT]").replace("⚠", "[WARN]").replace("✅", "[OK]").replace("❌", "[ERR]")
    # Drop any remaining non-Latin-1 characters
    return text.encode("latin-1", errors="ignore").decode("latin-1")


def generate_financial_pdf(symbol: str, analysis, stock_data) -> bytes:
    """Generates an Executive PDF Report containing stock metrics and LLM synthesis."""
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", style="B", size=24)
    pdf.cell(0, 15, f"{symbol} - Intelligence Report", new_x="LMARGIN", new_y="NEXT", align='L')
    
    pdf.set_font("Helvetica", size=12)
    pdf.cell(0, 10, f"Generated automatically by FITerminal Core", new_x="LMARGIN", new_y="NEXT", align='L')
    pdf.ln(10)
    
    # Metrics
    if stock_data:
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.cell(0, 8, "Key Statistics", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=12)
        pdf.cell(0, 8, f"Latest Price: ${stock_data.current_price:,.2f}", new_x="LMARGIN", new_y="NEXT")
        if stock_data.rsi:
            pdf.cell(0, 8, f"RSI (14d): {stock_data.rsi:.2f}", new_x="LMARGIN", new_y="NEXT")
        if stock_data.sma:
            pdf.cell(0, 8, f"SMA (20d): ${stock_data.sma:,.2f}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(10)
        
    # Analysis
    if analysis:
        pdf.set_font("Helvetica", style="B", size=14)
        pdf.cell(0, 8, f"Agent Verdict: {analysis.verdict} ({analysis.confidence}% Confidence)", new_x="LMARGIN", new_y="NEXT")
        
        pdf.set_font("Helvetica", size=12)
        pdf.multi_cell(0, 6, _safe(analysis.reasoning_summary))
        pdf.ln(5)
        
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, "Technical Signals", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        for t in analysis.technical_signals:
            pdf.multi_cell(0, 6, _safe(f"- {t.indicator}: {t.interpretation}"))
            
        pdf.ln(5)
        pdf.set_font("Helvetica", style="B", size=12)
        pdf.cell(0, 8, "Sentiment Signals", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", size=11)
        for s in analysis.sentiment_signals:
            pdf.multi_cell(0, 6, _safe(f"- {s.source} (Score {s.score}): {s.interpretation}"))
            
        if analysis.risk_assessment:
            pdf.ln(5)
            pdf.set_font("Helvetica", style="B", size=12)
            pdf.cell(0, 8, "Risk Context", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("Helvetica", size=11)
            pdf.multi_cell(0, 6, _safe(analysis.risk_assessment))
            
    return bytes(pdf.output())
