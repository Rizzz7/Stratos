# Stratos

## Elasticsearch connectivity

This project includes a small script to verify connectivity to an Elasticsearch 8.x cluster
using environment variables loaded via `python-dotenv`.

### Environment variables

- `ES_HOST`: Elasticsearch cloud URL, for example `https://your-cluster.es.eastus.azure.elastic-cloud.com`
- `ES_API_KEY`: Elasticsearch API key (base64 or `id:api_key` form)

### Run

```powershell
python run_elastic_search.py
```

## Elasticsearch ingest

This project includes a script that ingests civic notices from `data/civic_sources.json`
into the `startos-civic-sources` index.

### Run

```powershell
python run_ingest.py
```

## AWS Bedrock connectivity

This project includes a script that invokes Claude Sonnet via AWS Bedrock using
credentials loaded from `.env`.

### Environment variables

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_SESSION_TOKEN` (optional)

### Run

```powershell
python run_bedrock_client.py
```

