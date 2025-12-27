import os
import time
import json
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
import re

import requests
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv

# ------------- Setup -------------
load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

PROJECT_ID = "arboreal-logic-467306-k0"
DATASET_ID = "getmycouyselive"

# Klaviyo resources to sync - similar to Stripe multi-resource pattern
RESOURCES = [
    ('profiles', 'profiles'),
    ('events', 'events'),
    ('campaigns', 'campaigns'),
    ('flows', 'flows'),
    ('lists', 'lists'),
    ('segments', 'segments'),
    ('metrics', 'metrics'),
    ('tags', 'tags'),
    ('templates', 'templates'),
    ('catalog_items', 'catalog-items'),
    ('catalog_categories', 'catalog-categories'),
    ('coupons', 'coupons')
]

KLAVIYO_API_KEY = "pk_339d69a886bab5233b6d2f290dfe8ae376"
KLAVIYO_BASE = "https://a.klaviyo.com/api"

PER_PAGE = 100  # Klaviyo page size
SESSION = requests.Session()
SESSION_TIMEOUT = 60

# ------------- Helpers -------------
def _klaviyo_headers() -> Dict[str, str]:
    return {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "Accept": "application/json",
        "Content-Type": "application/json",
        "revision": "2024-10-15"
    }

def klaviyo_get(path: str, params: Dict[str, Any]) -> requests.Response:
    url = f"{KLAVIYO_BASE}/{path.lstrip('/')}"
    return SESSION.get(url, params=params, headers=_klaviyo_headers(), timeout=SESSION_TIMEOUT)

def fetch_klaviyo_profiles(modified_since: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch all profiles from Klaviyo API with pagination.
    """
    records: List[Dict[str, Any]] = []
    page_cursor = None
    
    while True:
        params = {
            "page[size]": PER_PAGE,
            "sort": "updated"
        }
        
        if page_cursor:
            params["page[cursor]"] = page_cursor
            
        if modified_since:
            params["filter"] = f"greater-than(updated,{modified_since})"
        
        resp = klaviyo_get("/profiles", params)
        
        if resp.status_code in (429, 502, 503, 504):
            # Backoff on rate/temporary errors
            logging.warning(f"Klaviyo temporary error {resp.status_code}. Backing off...")
            time.sleep(5)
            continue
            
        resp.raise_for_status()
        data = resp.json()
        
        page_records = data.get("data", [])
        if not page_records:
            break
            
        records.extend(page_records)
        logging.info(f"Fetched {len(page_records)} profiles | total so far: {len(records)}")
        
        # Check for next page
        links = data.get("links", {})
        next_link = links.get("next")
        if not next_link:
            break
            
        # Extract cursor from next link
        if "page%5Bcursor%5D=" in next_link:
            page_cursor = next_link.split("page%5Bcursor%5D=")[1].split("&")[0]
        else:
            break
            
        time.sleep(0.2)  # Rate limiting
    
    return records

def fetch_klaviyo_events(modified_since: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Fetch events from Klaviyo API with pagination.
    """
    records: List[Dict[str, Any]] = []
    page_cursor = None
    
    while True:
        params = {
            "page[size]": PER_PAGE,
            "sort": "-datetime"
        }
        
        if page_cursor:
            params["page[cursor]"] = page_cursor
            
        if modified_since:
            params["filter"] = f"greater-than(datetime,{modified_since})"
        
        resp = klaviyo_get("/events", params)
        
        if resp.status_code in (429, 502, 503, 504):
            logging.warning(f"Klaviyo temporary error {resp.status_code}. Backing off...")
            time.sleep(5)
            continue
            
        resp.raise_for_status()
        data = resp.json()
        
        page_records = data.get("data", [])
        if not page_records:
            break
            
        records.extend(page_records)
        logging.info(f"Fetched {len(page_records)} events | total so far: {len(records)}")
        
        # Check for next page
        links = data.get("links", {})
        next_link = links.get("next")
        if not next_link:
            break
            
        # Extract cursor from next link
        if "page%5Bcursor%5D=" in next_link:
            page_cursor = next_link.split("page%5Bcursor%5D=")[1].split("&")[0]
        else:
            break
            
        time.sleep(0.2)  # Rate limiting
    
    return records

# ---------- BQ field name sanitization ----------
def sanitize_field_names(obj):
    """Recursively sanitize field names to be BigQuery compatible."""
    if isinstance(obj, dict):
        sanitized = {}
        for key, value in obj.items():
            # Remove invalid characters and ensure valid field name
            clean_key = key.replace('$', 'dollar_').replace('@', 'at_').replace('#', 'hash_')
            clean_key = ''.join(c if c.isalnum() or c == '_' else '_' for c in clean_key)
            if clean_key and clean_key[0].isdigit():
                clean_key = 'field_' + clean_key
            if not clean_key:
                clean_key = 'unknown_field'
            sanitized[clean_key] = sanitize_field_names(value)
        return sanitized
    elif isinstance(obj, list):
        return [sanitize_field_names(item) for item in obj]
    else:
        return obj

def sanitize_field_name(field_name: str) -> str:
    """Sanitize field names for BigQuery compatibility."""
    # Replace invalid characters with underscores
    sanitized = re.sub(r'[^a-zA-Z0-9_]', '_', field_name)
    
    # Ensure it doesn't start with a number
    if sanitized and sanitized[0].isdigit():
        sanitized = f"field_{sanitized}"
    
    # Ensure it's not empty
    if not sanitized:
        sanitized = "unknown_field"
    
    return sanitized

def _sanitize_name(name: str) -> str:
    """
    Make a Klaviyo field name BigQuery-safe.
    """
    s = re.sub(r'[^A-Za-z0-9_]', '_', name)
    if not re.match(r'^[A-Za-z_]', s):
        s = '_' + s
    s = re.sub(r'_+', '_', s).strip('_')
    if not s:
        s = 'field'
    return s[:300]

def build_key_map(source_keys, reserved=None):
    """
    Build a deterministic map: original_name -> sanitized_name.
    """
    reserved = set(reserved or [])
    mapping = {}
    
    used_exact = set(reserved)
    used_lc = {c.lower() for c in reserved}
    
    for k in sorted(source_keys):
        base = _sanitize_name(k)
        candidate = base
        i = 2
        while candidate in used_exact or candidate.lower() in used_lc:
            candidate = f"{base}_{i}"
            i += 1
        mapping[k] = candidate
        used_exact.add(candidate)
        used_lc.add(candidate.lower())
    
    return mapping

def flatten_for_bq(record: Dict[str, Any], key_map: Dict[str, str], record_type: str) -> Dict[str, Any]:
    """
    Convert Klaviyo record to BigQuery format.
    """
    out: Dict[str, Any] = {}
    
    # Handle nested attributes
    attributes = record.get("attributes", {})
    
    # Flatten main record fields
    for k, v in record.items():
        if k == "attributes":
            continue  # Handle separately
        sk = key_map.get(k, _sanitize_name(k))
        
        if v is None:
            out[sk] = None
        elif isinstance(v, (dict, list)):
            out[sk] = json.dumps(v, ensure_ascii=False)
        else:
            out[sk] = str(v)
    
    # Flatten attributes
    for k, v in attributes.items():
        sk = key_map.get(f"attr_{k}", _sanitize_name(f"attr_{k}"))
        
        if v is None:
            out[sk] = None
        elif isinstance(v, (dict, list)):
            out[sk] = json.dumps(v, ensure_ascii=False)
        else:
            out[sk] = str(v)
    
    # Add metadata
    out["_ingested_at"] = datetime.now(timezone.utc).isoformat()
    out["_record_type"] = record_type
    out["_klaviyo_id"] = record.get("id")
    
    # Add updated timestamp if available
    if record_type == "profile":
        out["_updated_time"] = attributes.get("updated")
    elif record_type == "event":
        out["_event_time"] = attributes.get("datetime")
    
    return out

def ensure_dataset_and_tables(bq: bigquery.Client, resource_name: str):
    """Ensure the dataset and tables exist in BigQuery for a specific resource."""
    # Ensure dataset exists
    dataset = bigquery.Dataset(f"{PROJECT_ID}.{DATASET_ID}")
    try:
        bq.get_dataset(dataset)
    except Exception:
        dataset.location = "US"
        bq.create_dataset(dataset, exists_ok=True)
        logging.info(f"Created dataset {DATASET_ID}")
    
    # Create raw table for this resource
    raw_table_id = f"{PROJECT_ID}.{DATASET_ID}.klaviyo_{resource_name}_raw"
    raw_schema = [
        bigquery.SchemaField("_klaviyo_id", "STRING"),
        bigquery.SchemaField("_record_type", "STRING"),
        bigquery.SchemaField("_updated_time", "STRING"),
        bigquery.SchemaField("_event_time", "STRING"),
        bigquery.SchemaField("_ingested_at", "TIMESTAMP"),
        bigquery.SchemaField("data", "JSON")
    ]
    
    try:
        bq.get_table(raw_table_id)
    except Exception:
        raw_table = bigquery.Table(raw_table_id, schema=raw_schema)
        bq.create_table(raw_table, exists_ok=True)
        logging.info(f"Created raw table {raw_table_id}")
    
    # Create final table for this resource
    final_table_id = f"{PROJECT_ID}.{DATASET_ID}.klaviyo_{resource_name}"
    final_schema = [
        bigquery.SchemaField("_klaviyo_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("_record_type", "STRING"),
        bigquery.SchemaField("_ingested_at", "TIMESTAMP"),
        bigquery.SchemaField("_updated_time", "TIMESTAMP"),
        bigquery.SchemaField("_event_time", "TIMESTAMP"),
    ]
    
    try:
        bq.get_table(final_table_id)
    except Exception:
        final_table = bigquery.Table(final_table_id, schema=final_schema)
        bq.create_table(final_table, exists_ok=True)
        logging.info(f"Created final table {final_table_id}")
    
    return raw_table_id, final_table_id

def sync_final_schema_with_raw(bq: bigquery.Client, raw_table_id: str, final_table_id: str):
    """Sync final table schema with raw table schema."""
    raw_tbl = raw_table_id.split(".")[-1]
    final_tbl = final_table_id.split(".")[-1]
    
    q_raw = f"""
      SELECT column_name FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
      WHERE table_name = '{raw_tbl}'
    """
    q_final = f"""
      SELECT column_name FROM `{PROJECT_ID}.{DATASET_ID}.INFORMATION_SCHEMA.COLUMNS`
      WHERE table_name = '{final_tbl}'
    """
    
    raw_cols = [r["column_name"] for r in bq.query(q_raw).result()]
    final_cols = {r["column_name"] for r in bq.query(q_final).result()}
    
    table = bq.get_table(final_table_id)
    existing = {f.name: f for f in table.schema}
    new_fields = []
    
    for c in raw_cols:
        if c in final_cols:
            continue
        if c in {"_ingested_at", "_updated_time", "_event_time"}:
            new_fields.append(bigquery.SchemaField(c, "TIMESTAMP"))
        elif c in {"_klaviyo_id", "_record_type"}:
            new_fields.append(bigquery.SchemaField(c, "STRING"))
        else:
            new_fields.append(bigquery.SchemaField(c, "STRING"))
    
    if new_fields:
        table.schema = list(existing.values()) + new_fields
        bq.update_table(table, ["schema"])
        logging.info(f"Extended {final_table_id} with {len(new_fields)} columns")

def merge_raw_to_final(bq: bigquery.Client, raw_table_id: str, final_table_id: str):
    """Merge latest records from raw to final table."""
    sync_final_schema_with_raw(bq, raw_table_id, final_table_id)
    
    # Direct merge without temp table
    merge_sql = f"""
    MERGE `{final_table_id}` T
    USING (
      SELECT * EXCEPT(row_num)
      FROM (
        SELECT r.*,
               ROW_NUMBER() OVER (
                 PARTITION BY _klaviyo_id, _record_type
                 ORDER BY _updated_time DESC NULLS LAST, _event_time DESC NULLS LAST, _ingested_at DESC
               ) AS row_num
        FROM `{raw_table_id}` r
      )
      WHERE row_num = 1
    ) S
    ON T._klaviyo_id = S._klaviyo_id AND T._record_type = S._record_type
    WHEN MATCHED THEN
      UPDATE SET
        T._ingested_at = S._ingested_at,
        T._updated_time = S._updated_time,
        T._event_time = S._event_time
    WHEN NOT MATCHED THEN
      INSERT ROW
    """
    
    # Execute the merge
    bq.query(merge_sql).result()
    logging.info(f"Merged into {final_table_id}")

def fetch_klaviyo_campaigns():
    """Fetch campaigns from Klaviyo API (Email and SMS)."""
    url = f"{KLAVIYO_BASE}/campaigns/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-10-15"
    }
    
    all_campaigns = []
    
    # Campaign endpoint requires a filter for channel (email or sms)
    # We will fetch both and combine them
    for channel in ['email', 'sms']:
        logging.info(f"Fetching {channel} campaigns...")
        page_cursor = None
        
        while True:
            # Note: campaigns endpoint does not support page[size]
            params = {"filter": f"equals(messages.channel,'{channel}')"}
            if page_cursor:
                params["page[cursor]"] = page_cursor
            
            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()
                data = response.json()
                
                campaigns = data.get("data", [])
                all_campaigns.extend(campaigns)
                
                # Check for next page
                links = data.get("links", {})
                if "next" not in links:
                    break
                
                page_cursor = links["next"].split("page[cursor]=")[-1].split("&")[0]
                
                # Rate limiting
                time.sleep(0.1)
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Error fetching {channel} campaigns: {e}")
                break
    
    return all_campaigns

def fetch_klaviyo_flows():
    """Fetch flows from Klaviyo API."""
    url = f"{KLAVIYO_BASE}/flows/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-10-15"
    }
    
    all_flows = []
    page_cursor = None
    
    while True:
        params = {"page[size]": 100}
        if page_cursor:
            params["page[cursor]"] = page_cursor
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            flows = data.get("data", [])
            all_flows.extend(flows)
            
            # Check for next page
            links = data.get("links", {})
            if "next" not in links:
                break
            
            page_cursor = links["next"].split("page[cursor]=")[-1].split("&")[0]
            
            # Rate limiting
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching flows: {e}")
            break
    
    return all_flows

def fetch_klaviyo_lists():
    """Fetch lists from Klaviyo API."""
    url = f"{KLAVIYO_BASE}/lists/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-10-15"
    }
    
    all_lists = []
    page_cursor = None
    
    while True:
        # Note: lists endpoint does not support page[size]
        params = {}
        if page_cursor:
            params["page[cursor]"] = page_cursor
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            lists = data.get("data", [])
            all_lists.extend(lists)
            
            # Check for next page
            links = data.get("links", {})
            if "next" not in links:
                break
            
            page_cursor = links["next"].split("page[cursor]=")[-1].split("&")[0]
            
            # Rate limiting
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching lists: {e}")
            break
    
    return all_lists

def fetch_klaviyo_segments():
    """Fetch segments from Klaviyo API."""
    url = f"{KLAVIYO_BASE}/segments/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-10-15"
    }
    
    all_segments = []
    page_cursor = None
    
    while True:
        # Note: segments endpoint does not support page[size]
        params = {}
        if page_cursor:
            params["page[cursor]"] = page_cursor
        
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()
            
            segments = data.get("data", [])
            all_segments.extend(segments)
            
            # Check for next page
            links = data.get("links", {})
            if "next" not in links:
                break
            
            page_cursor = links["next"].split("page[cursor]=")[-1].split("&")[0]
            
            # Rate limiting
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching segments: {e}")
            break
    
    return all_segments

def fetch_klaviyo_metrics():
    """Fetch metrics from Klaviyo API."""
    url = f"{KLAVIYO_BASE}/metrics/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-10-15"
    }
    
    all_metrics = []
    page_cursor = None
    
    while True:
        # Note: metrics endpoint does not support page[size]
        params = {}
        if page_cursor:
            params["page[cursor]"] = page_cursor
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            # Log the response for debugging
            if response.status_code != 200:
                logging.error(f"Metrics API error {response.status_code}: {response.text}")
                # If metrics endpoint is not accessible, return empty list
                if response.status_code == 400:
                    logging.warning("Metrics endpoint may not be available for this account. Skipping metrics sync.")
                    return []
            
            response.raise_for_status()
            data = response.json()
            
            metrics = data.get("data", [])
            all_metrics.extend(metrics)
            
            # Check for next page
            links = data.get("links", {})
            if "next" not in links:
                break
            
            page_cursor = links["next"].split("page[cursor]=")[-1].split("&")[0]
            
            # Rate limiting
            time.sleep(0.2)  # Increased delay for metrics
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching metrics: {e}")
            # For metrics, we'll gracefully handle the error and return empty list
            logging.warning("Continuing without metrics data due to API limitations")
            return []
    
    return all_metrics

def fetch_klaviyo_simple_resource(resource_endpoint: str) -> List[Dict[str, Any]]:
    """Fetch a resource that does not support page[size] parameter."""
    url = f"{KLAVIYO_BASE}/{resource_endpoint}/"
    headers = {
        "Authorization": f"Klaviyo-API-Key {KLAVIYO_API_KEY}",
        "revision": "2024-10-15"
    }
    
    all_records = []
    page_cursor = None
    
    while True:
        params = {}
        if page_cursor:
            params["page[cursor]"] = page_cursor
        
        try:
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code != 200:
                logging.error(f"{resource_endpoint} API error {response.status_code}: {response.text}")
                if response.status_code == 400:
                    logging.warning(f"{resource_endpoint} endpoint may not be available. Skipping.")
                    return []
            
            response.raise_for_status()
            data = response.json()
            
            records = data.get("data", [])
            all_records.extend(records)
            
            # Check for next page
            links = data.get("links", {})
            if "next" not in links:
                break
            
            page_cursor = links["next"].split("page[cursor]=")[-1].split("&")[0]
            
            # Rate limiting
            time.sleep(0.1)
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching {resource_endpoint}: {e}")
            break
    
    return all_records

def sync_resource(bq: bigquery.Client, resource_name: str, endpoint: str):
    """Sync a specific Klaviyo resource to BigQuery."""
    logging.info(f"Starting sync for {resource_name}...")
    
    # Ensure tables exist for this resource
    raw_table_id, final_table_id = ensure_dataset_and_tables(bq, resource_name)
    
    all_records = []
    
    # Fetch data based on resource type
    if resource_name == "profiles":
        data = fetch_klaviyo_profiles()
        record_type = "profile"
    elif resource_name == "events":
        data = fetch_klaviyo_events()
        record_type = "event"
    elif resource_name == "campaigns":
        data = fetch_klaviyo_campaigns()
        record_type = "campaign"
    elif resource_name == "flows":
        data = fetch_klaviyo_flows()
        record_type = "flow"
    elif resource_name == "lists":
        data = fetch_klaviyo_lists()
        record_type = "list"
    elif resource_name == "segments":
        data = fetch_klaviyo_segments()
        record_type = "segment"
    elif resource_name == "metrics":
        data = fetch_klaviyo_metrics()
        record_type = "metric"
    elif resource_name in ["tags", "templates", "catalog_items", "catalog_categories", "coupons"]:
        data = fetch_klaviyo_simple_resource(endpoint)
        record_type = resource_name.replace("_", "-").rstrip('s') # simple heuristic for record type
    else:
        logging.info(f"Unknown resource type: {resource_name}")
        return
    
    if not data:
        logging.info(f"No {resource_name} data to process")
        return
    
    logging.info(f"Fetched {len(data)} {resource_name}")
    
    # Build key mapping from all records
    all_keys = set()
    for record in data:
        all_keys.update(record.keys())
        if "attributes" in record:
            all_keys.update([f"attr_{k}" for k in record["attributes"].keys()])
    
    key_map = build_key_map(all_keys, reserved=["_ingested_at", "_record_type", "_klaviyo_id", "_updated_time", "_event_time"])
    
    # Transform records
    for record in data:
        flattened = flatten_for_bq(record, key_map, record_type)
        all_records.append(flattened)
    
    if all_records:
        # Sanitize field names to be BigQuery compatible
        sanitized_records = [sanitize_field_names(record) for record in all_records]
        
        # Load to raw table
        logging.info(f"Loading {len(sanitized_records)} {resource_name} records to raw table...")
        
        # Auto-detect schema
        job_config = bigquery.LoadJobConfig(
            write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,  # Use TRUNCATE to allow schema evolution
            autodetect=True
        )
        
        job = bq.load_table_from_json(sanitized_records, raw_table_id, job_config=job_config)
        job.result()
        
        logging.info(f"✅ Loaded {len(all_records)} {resource_name} records to raw table")
        
        # Merge to final table
        logging.info(f"Merging {resource_name} to final table...")
        merge_raw_to_final(bq, raw_table_id, final_table_id)
        logging.info(f"✅ {resource_name} sync completed")
    else:
        logging.info(f"No {resource_name} records to load")

def main():
    """Main function to fetch Klaviyo data and load to BigQuery."""
    logging.info("Starting Klaviyo → BigQuery sync")
    
    # Initialize BigQuery client
    credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "./credentials/arboreal-logic-467306-k0-137d44e4d27e.json")
    credentials = service_account.Credentials.from_service_account_file(credentials_path)
    bq = bigquery.Client(credentials=credentials, project=PROJECT_ID)
    
    # Sync each resource
    for resource_name, endpoint in RESOURCES:
        try:
            sync_resource(bq, resource_name, endpoint)
        except Exception as e:
            logging.error(f"Failed to sync {resource_name}: {e}")
            continue
    
    logging.info("✅ All Klaviyo resources sync completed")

if __name__ == "__main__":
    main()