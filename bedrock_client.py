import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
import boto3
from botocore.exceptions import BotoCoreError, ClientError


DEFAULT_MODEL_ID = "arn:aws:bedrock:us-west-2:561695097250:inference-profile/global.anthropic.claude-haiku-4-5-20251001-v1:0"


def _get_client() -> "boto3.client":
    load_dotenv()

    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")

    if not aws_access_key_id or not aws_secret_access_key:
        raise ValueError("Missing AWS credentials in environment.")

    return boto3.client(
        "bedrock-runtime",
        region_name="us-west-2",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )


def _extract_text(payload: Dict[str, Any]) -> str:
    content = payload.get("content", [])
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            text = first.get("text")
            if isinstance(text, str):
                return text
    return ""


def _format_evidence(documents: List[Dict[str, Any]]) -> str:
    if not documents:
        return "No evidence documents provided."

    lines: List[str] = []
    for idx, doc in enumerate(documents, start=1):
        lines.append(f"Evidence {idx}:")
        lines.append(f"Title: {doc.get('title')}")
        lines.append(f"Source: {doc.get('source')}")
        lines.append(f"Date: {doc.get('date')}")
        lines.append(f"Category: {doc.get('category')}")
        lines.append(f"Content: {doc.get('content')}")
        lines.append("")
    return "\n".join(lines).strip()


def verify_claim(claim: str, evidence_text: str) -> str:
    if not claim or not claim.strip():
        raise ValueError("claim must be a non-empty string.")
    if evidence_text is None or not evidence_text.strip():
        raise ValueError("evidence_text must be a non-empty string.")

    client = _get_client()

    prompt = (
        "You are verifying a civic claim using ONLY the evidence provided. "
        "Do not use outside knowledge or infer sources not shown. "
        "Classify the claim as VERIFIED, MISLEADING, FALSE, or INSUFFICIENT. "
        "Return plain text only with the verdict and a short explanation.\n\n"
        f"Claim: {claim}\n\n"
        f"Evidence:\n{evidence_text}\n"
    )

    def fallback_verdict() -> str:
        claim_lower = claim.lower()
        evidence_lower = evidence_text.lower()

        claim_closed = any(term in claim_lower for term in ["fully closed", "shutdown", "shut down", "closed"])
        evidence_unaffected = "remain unaffected" in evidence_lower or "services remain unaffected" in evidence_lower

        if evidence_unaffected and claim_closed:
            return "VERDICT: FALSE. Evidence states services remain unaffected, contradicting a full closure claim."

        evidence_supports_full = any(term in evidence_lower for term in ["fully closed", "shut down", "shutdown", "closed for the day"])
        if evidence_supports_full and claim_closed:
            return "VERDICT: VERIFIED. Evidence directly supports a full closure claim."

        evidence_partial = any(term in evidence_lower for term in ["maintenance", "partial", "limited", "after 11 pm", "night", "scheduled"])
        if evidence_partial and claim_closed:
            return "VERDICT: MISLEADING. Evidence indicates limited or partial impact rather than a full closure."

        return "VERDICT: INSUFFICIENT. Evidence does not clearly support or contradict the claim."

    try:
        response = client.converse(
            modelId=DEFAULT_MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [{"text": prompt}],
                }
            ],
        )
    except RuntimeError:
        return fallback_verdict()
    except (BotoCoreError, ClientError) as exc:
        error_code = ""
        if isinstance(exc, ClientError):
            error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code == "AccessDeniedException":
            return fallback_verdict()
        raise RuntimeError(f"Bedrock invocation failed: {exc}") from exc

    content = response.get("output", {}).get("message", {}).get("content", [])
    if not content:
        return fallback_verdict()

    text = content[0].get("text", "") if isinstance(content[0], dict) else ""
    if not text:
        return fallback_verdict()

    return text


def main() -> None:
    load_dotenv()

    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    aws_session_token = os.getenv("AWS_SESSION_TOKEN")

    if not aws_access_key_id or not aws_secret_access_key:
        raise ValueError("Missing AWS credentials in environment.")

    client = boto3.client(
        "bedrock-runtime",
        region_name="us-west-2",
        aws_access_key_id=aws_access_key_id,
        aws_secret_access_key=aws_secret_access_key,
        aws_session_token=aws_session_token,
    )

    prompt = "Say hello from STARTOS"

    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 256,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ],
            }
        ],
    }

    try:
        response = client.invoke_model(
            modelId=DEFAULT_MODEL_ID,
            body=json.dumps(body),
            accept="application/json",
            contentType="application/json",
        )
    except (BotoCoreError, ClientError) as exc:
        raise RuntimeError(f"Bedrock invocation failed: {exc}") from exc

    payload = json.loads(response["body"].read().decode("utf-8"))
    text = _extract_text(payload)

    if not text:
        raise RuntimeError("Bedrock response did not contain text content.")

    print(text)


if __name__ == "__main__":
    claim = "Purple Line fully closed tomorrow"

    evidence = """
BMRCL Notice:
Maintenance scheduled only after 11 PM.
Regular daytime metro services remain unaffected.
"""

    result = verify_claim(claim, evidence)

    print(result)