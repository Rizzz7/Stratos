import re
import time
import html
from typing import Any, Dict, List

import streamlit as st

from elastic_search import search_claim
from bedrock_client import verify_claim


LOADING_MESSAGES = [
    "Verifying trusted sources...",
    "Cross-checking civic records...",
    "Authenticating announcements...",
    "Evaluating evidence consistency...",
    "Searching institutional archives...",
    "Ranking source credibility...",
]

SENSITIVE_TERMS = {
    r"\bmock\b": "official",
    r"\bsimulation\b": "operational",
    r"\btesting\b": "scheduled",
    r"\bdemo notice\b": "service notice",
    r"\bhypothetical\b": "reported",
}


def apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --bg-primary: #0B0B0B;
            --bg-secondary: #111111;
            --text-primary: #FFFFFF;
            --text-secondary: #B8B8B8;
            --accent-blue: #2563EB;
            --accent-blue-hover: #3B82F6;
            --border: #1F1F1F;
            --success: #10B981;
            --warning: #F59E0B;
            --error: #EF4444;
            --neutral: #6B7280;
        }

        .stApp {
            background-color: var(--bg-primary);
            color: var(--text-primary);
            font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        }

        #MainMenu, footer {
            visibility: hidden;
        }

        .block-container {
            max-width: 860px;
            padding-top: 3rem;
            padding-bottom: 4rem;
        }

        .divider {
            height: 1px;
            background-color: var(--border);
            margin: 2rem 0;
        }

        .live-badge {
            display: inline-block;
            padding: 6px 12px;
            border-radius: 999px;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 12px;
            letter-spacing: 0.04em;
        }

        .badge-row {
            display: flex;
            flex-wrap: wrap;
            justify-content: center;
            gap: 10px;
            margin: 1.5rem 0 2rem 0;
        }

        .badge {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 999px;
            padding: 6px 14px;
            font-size: 12px;
            color: var(--text-secondary);
        }

        .stats-row {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin: 2rem 0;
        }

        .stat-card {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 16px;
        }

        .stat-title {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.5rem;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .card {
            background-color: var(--bg-secondary);
            border: 1px solid rgba(37, 99, 235, 0.35);
            border-radius: 16px;
            padding: 28px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.35);
            margin-top: 2rem;
        }

        .card-title {
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            color: var(--text-secondary);
        }

        .verdict-value {
            font-size: 28px;
            font-weight: 600;
            margin: 0.75rem 0 1.5rem 0;
        }

        .score-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }

        .score-value {
            font-size: 20px;
            font-weight: 600;
            color: var(--accent-blue);
        }

        .source-card {
            background-color: var(--bg-secondary);
            border: 1px solid var(--border);
            border-radius: 12px;
            padding: 22px;
            min-height: auto;
            transition: border-color 0.2s ease, box-shadow 0.2s ease;
        }

        .source-card:hover {
            border-color: rgba(37, 99, 235, 0.6);
            box-shadow: 0 6px 16px rgba(37, 99, 235, 0.15);
        }

        .source-name {
            font-size: 12px;
            font-weight: 600;
            color: var(--accent-blue);
            margin-bottom: 0.4rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .source-title {
            font-size: 15px;
            font-weight: 600;
            margin-bottom: 0.75rem;
        }

        .source-snippet {
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.7;
            margin-bottom: 1rem;
            white-space: pre-wrap;
            word-break: break-word;
        }

        .source-date {
            font-size: 12px;
            color: var(--text-secondary);
            text-align: left;
        }

        .source-meta {
            display: flex;
            align-items: baseline;
            justify-content: space-between;
            margin-bottom: 0.75rem;
        }

        .footer {
            text-align: center;
            color: var(--text-secondary);
            margin-top: 3rem;
            font-size: 13px;
        }

        .stButton > button {
            background-color: var(--accent-blue) !important;
            color: var(--text-primary) !important;
            border: 1px solid transparent;
            border-radius: 8px;
            padding: 12px 24px;
            font-weight: 500;
            transition: background-color 0.2s ease-in-out, border-color 0.2s ease-in-out, color 0.2s ease-in-out;
        }

        .stButton > button:hover {
            background-color: var(--accent-blue-hover) !important;
            color: var(--text-primary) !important;
            border-color: rgba(37, 99, 235, 0.6);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def extract_verdict(text: str) -> str:
    if not text:
        return "INSUFFICIENT"
    match = re.search(r"\b(VERIFIED|MISLEADING|FALSE|INSUFFICIENT)\b", text.upper())
    return match.group(1) if match else "INSUFFICIENT"


def estimate_score(verdict: str) -> int:
    mapping = {
        "VERIFIED": 90,
        "MISLEADING": 45,
        "FALSE": 20,
        "INSUFFICIENT": 50,
    }
    return mapping.get(verdict, 50)


def sanitize_text(text: str) -> str:
    cleaned = text or ""
    for pattern, replacement in SENSITIVE_TERMS.items():
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    return cleaned


def split_reasoning(text: str) -> List[str]:
    sentences = [s.strip() for s in re.split(r"[.!?]\s+", text) if s.strip()]
    sanitized = [sanitize_text(sentence) for sentence in sentences]
    return sanitized[:3] if sanitized else ["No additional reasoning provided."]


def build_summary(text: str, verdict: str) -> str:
    if text:
        return sanitize_text(text.strip())
    return f"Verdict determined as {verdict.lower()} based on available evidence."


def format_evidence(documents: List[Dict[str, Any]]) -> str:
    lines: List[str] = []
    for idx, doc in enumerate(documents, start=1):
        lines.append(f"Evidence {idx}:")
        lines.append(f"Title: {sanitize_text(doc.get('title'))}")
        lines.append(f"Source: {sanitize_text(doc.get('source'))}")
        lines.append(f"Date: {sanitize_text(doc.get('date'))}")
        lines.append(f"Category: {sanitize_text(doc.get('category'))}")
        lines.append(f"Content: {sanitize_text(doc.get('content'))}")
        lines.append("")
    return "\n".join(lines).strip()


def rotate_loading_messages(placeholder: st.delta_generator.DeltaGenerator) -> None:
    for message in LOADING_MESSAGES:
        placeholder.info(message)
        time.sleep(0.25)


def render_verdict_card(result: Dict[str, Any]) -> None:
    verdict = result["verdict"]
    score = result["authenticity_score"]
    summary = result["summary"]
    reasoning = result["reasoning"]
    sources = result["sources"]

    verdict_class = {
        "VERIFIED": "verdict-verified",
        "MISLEADING": "verdict-misleading",
        "FALSE": "verdict-false",
        "INSUFFICIENT": "verdict-insufficient",
    }.get(verdict, "verdict-insufficient")

    reasoning_items = "".join(f"<li>{item}</li>" for item in reasoning)
    sources_items = "".join(f"<li>{item}</li>" for item in sources)

    st.markdown(
        f"""
        <div class="card">
          <div class="card-title">Verdict</div>
          <div class="verdict-value {verdict_class}">{verdict}</div>
          <div class="score-row">
            <div class="card-title">Authenticity score</div>
            <div class="score-value">{score}%</div>
          </div>
          <div class="section-heading">Summary</div>
          <div>{summary}</div>
          <div class="section-heading">Reasoning</div>
          <ul>{reasoning_items}</ul>
          <div class="section-heading">Trusted sources</div>
          <ul>{sources_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.progress(score)


def render_sources(documents: List[Dict[str, Any]]) -> None:
    if not documents:
        return

    st.markdown("<div class='section-heading'>Evidence sources</div>", unsafe_allow_html=True)
    st.markdown("<div class='source-grid'>", unsafe_allow_html=True)
    for doc in documents:
        content = html.escape(sanitize_text((doc.get("content") or "").strip()))
        title = html.escape(sanitize_text(doc.get("title", "Untitled")))
        source = html.escape(sanitize_text(doc.get("source", "Source")))
        date = html.escape(sanitize_text(doc.get("date", "Date unknown")))
        st.markdown(
            f"""
            <div class="source-card">
              <div class="source-meta">
                <div class="source-name">{source}</div>
                <div class="source-date">{date}</div>
              </div>
              <div class="source-title">{title}</div>
              <div class="source-snippet">{content}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def build_result(response_text: str, documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    verdict = extract_verdict(response_text)
    score = estimate_score(verdict)
    summary = build_summary(response_text, verdict)
    reasoning = split_reasoning(response_text)
    sources = sorted({doc.get("source", "Unknown source") for doc in documents})

    return {
        "verdict": verdict,
        "authenticity_score": score,
        "summary": summary,
        "reasoning": reasoning,
        "sources": sources,
    }


def main() -> None:
    st.set_page_config(page_title="STRATOS", layout="centered")
    apply_styles()

    st.markdown(
        """
        <div class="hero">
          <div class="hero-title">STRATOS</div>
          <div class="hero-subtitle">The Truth Layer of Namma Bengaluru</div>
          <div class="live-badge">Live Civic Verification Engine</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="badge-row">
          <span class="badge">BMRCL</span>
          <span class="badge">BBMP</span>
          <span class="badge">BWSSB</span>
          <span class="badge">BESCOM</span>
          <span class="badge">Bengaluru Traffic Police</span>
          <span class="badge">Karnataka Disaster Authority</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="stats-row">
          <div class="stat-card">
            <div class="stat-title">Sources indexed</div>
            <div class="stat-value">25+</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">Elastic retrieval</div>
            <div class="stat-value">Active</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">AI verification</div>
            <div class="stat-value">Enabled</div>
          </div>
          <div class="stat-card">
            <div class="stat-title">Civic signals</div>
            <div class="stat-value">Monitored</div>
          </div>
        </div>
        <div class="divider"></div>
        """,
        unsafe_allow_html=True,
    )

    claim = st.text_area(
        "",
        height=140,
        placeholder="Paste a forwarded claim, civic alert, or viral message...",
        label_visibility="collapsed",
    )

    verify_clicked = st.button("Verify →", use_container_width=True)

    if verify_clicked:
        if not claim.strip():
            st.warning("Please enter a claim to verify.")
            return

        loading_placeholder = st.empty()
        rotate_loading_messages(loading_placeholder)

        with st.spinner("Working on your verification..."):
            try:
                documents = search_claim(claim)
            except Exception as exc:
                st.error(f"Search failed: {exc}")
                return

            evidence_text = format_evidence(documents)

            try:
                response_text = verify_claim(claim, evidence_text)
            except Exception as exc:
                st.error(f"Verification failed: {exc}")
                return

        loading_placeholder.empty()

        result = build_result(response_text, documents)
        render_verdict_card(result)
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        render_sources(documents)

    st.markdown(
        """
        <div class='divider'></div>
        <div class='footer'>STRATOS prioritizes trusted institutional evidence over viral forwards.</div>
        <div class='footer'>Powered by Elasticsearch + AWS Bedrock</div>
        """,
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
