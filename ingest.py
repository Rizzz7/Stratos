import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from elasticsearch import ApiError, Elasticsearch
from elasticsearch.helpers import bulk


INDEX_NAME = "startos-civic-sources"
DATA_PATH = os.path.join("data", "civic_sources.json")


def _load_records(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("JSON data must be an array of objects.")
    return data


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

        if not es.indices.exists(index=INDEX_NAME):
            es.indices.create(index=INDEX_NAME)

        records = _load_records(DATA_PATH)
        actions = [
            {"_index": INDEX_NAME, "_source": record}
            for record in records
        ]

        inserted, _ = bulk(es, actions)
        print(f"Inserted {inserted} records successfully")
    except (ApiError, OSError, ValueError) as exc:
        raise RuntimeError(f"Ingestion failed: {exc}") from exc


if __name__ == "__main__":
    main()

