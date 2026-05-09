import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from elasticsearch import ApiError, Elasticsearch


INDEX_NAME = "startos-civic-sources"


def _get_client() -> Elasticsearch:
    load_dotenv()

    es_host = os.getenv("ES_HOST")
    es_api_key = os.getenv("ES_API_KEY")

    if not es_host or not es_api_key:
        raise ValueError("Missing ES_HOST or ES_API_KEY in environment.")

    return Elasticsearch(
        es_host,
        api_key=es_api_key,
    )


def search_claim(claim: str) -> List[Dict[str, Any]]:
    if not claim or not claim.strip():
        raise ValueError("Claim must be a non-empty string.")

    es = _get_client()

    query = {
        "multi_match": {
            "query": claim,
            "fields": ["title", "content", "category"],
        }
    }

    try:
        response = es.search(
            index=INDEX_NAME,
            size=3,
            query=query,
        )
    except ApiError as exc:
        raise RuntimeError(f"Elasticsearch search failed: {exc}") from exc

    hits = response.get("hits", {}).get("hits", [])
    results: List[Dict[str, Any]] = []

    for hit in hits:
        source = hit.get("_source", {})
        results.append(
            {
                "title": source.get("title"),
                "source": source.get("source"),
                "content": source.get("content"),
                "date": source.get("date"),
                "category": source.get("category"),
                "relevance_score": hit.get("_score"),
            }
        )

    return results


def main() -> None:
    load_dotenv()

    es_host = os.getenv("ES_HOST")
    es_api_key = os.getenv("ES_API_KEY")

    if not es_host or not es_api_key:
        raise ValueError("Missing ES_HOST or ES_API_KEY in environment.")

    es = Elasticsearch(
        es_host,
        api_key=es_api_key,
    )

    try:
        if not es.ping():
            raise RuntimeError("Elasticsearch ping failed.")

        print("Connected to Elasticsearch successfully")

        info = es.info()
        print("Cluster info:")
        print(json.dumps(info.body, indent=2, sort_keys=True))
    except ApiError as exc:
        raise RuntimeError(f"Elasticsearch API error: {exc}") from exc


if __name__ == "__main__":
    main()


results = search_claim("Purple Line shutdown tomorrow")

for r in results:
    print(r)