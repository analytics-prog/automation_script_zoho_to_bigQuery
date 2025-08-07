#!/usr/bin/env python3
"""
Main Zoho CRM to BigQuery AutoSync
Unified script to sync Leads, Deals, and Deals Complete data
"""

import os
import sys
import json
import time
import logging
import argparse
import schedule
import requests
import traceback
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dotenv import load_dotenv
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
from google.oauth2 import service_account



# Load environment variables
load_dotenv()

# Add parent directory to path for config imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configurations
try:
    from config.config import ZOHO_FIELD_MAPPINGS as LEADS_FIELD_MAPPINGS, BIGQUERY_CONFIG as LEADS_CONFIG, BATCH_CONFIG as LEADS_BATCH_CONFIG
    from config.deals_config import DEALS_FIELD_MAPPINGS, BIGQUERY_CONFIG as DEALS_CONFIG, BATCH_CONFIG as DEALS_BATCH_CONFIG, DEALS_BIGQUERY_SCHEMA
    from config.deals_complete_config import COMPLETE_DEALS_FIELD_MAPPINGS, BIGQUERY_CONFIG as DEALS_COMPLETE_CONFIG, BATCH_CONFIG as DEALS_COMPLETE_BATCH_CONFIG
except ImportError as e:
    print(f"Error importing config modules: {e}")
    print("Please ensure config files are available")
    sys.exit(1)

# Define leads schema based on field mappings
LEADS_BIGQUERY_SCHEMA = [
    {'name': 'lead_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'lead_owner', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'lead_source', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'lead_status', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'lead_type', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'lead_status_stage', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'email', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'phone', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'mobile', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'secondary_email', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'first_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'last_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'title', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'company', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'industry', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'date_of_birth', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'visa_type', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'street', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'city', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'state', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'zip_code', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'country', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'created_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    {'name': 'modified_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    {'name': 'created_by', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'modified_by', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'sync_timestamp', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    {'name': 'sync_source', 'type': 'STRING', 'mode': 'NULLABLE'},
]

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'main_autosync.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ZohoCRMClient:
    """Unified Zoho CRM client for all data types"""
    
    def __init__(self):
        self.client_id = os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        self.refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
        self.domain = os.getenv('ZOHO_DOMAIN', 'com.au')
        self.access_token = None
        
        if not all([self.client_id, self.client_secret, self.refresh_token]):
            raise ValueError("Missing required Zoho CRM credentials in environment variables")
    
    def get_access_token(self) -> str:
        """Get access token using refresh token"""
        if self.access_token:
            return self.access_token
            
        url = f"https://accounts.zoho.{self.domain}/oauth/v2/token"
        data = {
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(url, data=data)
        if response.status_code == 200:
            token_data = response.json()
            self.access_token = token_data['access_token']
            logger.info("Successfully obtained Zoho access token")
            return self.access_token
        else:
            raise Exception(f"Failed to get access token: {response.text}")
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers for API requests"""
        return {
            'Authorization': f'Zoho-oauthtoken {self.get_access_token()}',
            'Content-Type': 'application/json'
        }
    
    def get_records(self, module: str, since_time: Optional[datetime] = None, page: int = 1, per_page: int = 200) -> List[Dict[str, Any]]:
        """Fetch records from any Zoho CRM module"""
        url = f"https://www.zohoapis.{self.domain}/crm/v2/{module}"
        
        params = {
            'page': page,
            'per_page': per_page,
            'sort_order': 'desc',
            'sort_by': 'Modified_Time'
        }
        
        if since_time:
            formatted_time = since_time.replace(microsecond=0).isoformat() + 'Z'
            params['If-Modified-Since'] = formatted_time
            logger.info(f"Fetching {module} modified since: {formatted_time}")
        
        try:
            response = requests.get(url, headers=self.get_headers(), params=params)
            
            if response.status_code == 200:
                data = response.json()
                records = data.get('data', [])
                logger.info(f"Successfully fetched {len(records)} {module} from page {page}")
                return records
            elif response.status_code == 304:
                logger.info(f"No new {module} found (304 Not Modified)")
                return []
            else:
                logger.error(f"Error fetching {module}: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Exception while fetching {module}: {str(e)}")
            return []
    
    def get_all_records(self, module: str, since_time: Optional[datetime] = None, batch_size: int = 200) -> List[Dict[str, Any]]:
        """Fetch all records with pagination"""
        all_records = []
        page = 1
        
        while True:
            records = self.get_records(module, since_time, page, batch_size)
            
            if not records:
                break
                
            all_records.extend(records)
            
            if len(records) < batch_size:
                break
                
            page += 1
            time.sleep(0.5)  # Be respectful to the API
        
        logger.info(f"Total {module} fetched: {len(all_records)}")
        return all_records



class BigQueryClient:
    """Unified BigQuery client for all data types"""
    
    def __init__(self):
        self.project_id = os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        
        if not self.project_id:
            raise ValueError("Missing GOOGLE_CLOUD_PROJECT_ID environment variable")
        
        self.client = bigquery.Client(project=self.project_id)
    
    def ensure_dataset_exists(self, dataset_id: str, location: str = 'US'):
        """Create dataset if it doesn't exist"""
        dataset_ref = self.client.dataset(dataset_id)
        
        try:
            self.client.get_dataset(dataset_ref)
            logger.info(f"Dataset {dataset_id} already exists")
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = location
            dataset = self.client.create_dataset(dataset)
            logger.info(f"Created dataset {dataset_id}")
    
    def ensure_table_exists(self, dataset_id: str, table_id: str, schema: List[Dict]):
        """Create table if it doesn't exist"""
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        
        try:
            self.client.get_table(table_ref)
            logger.info(f"Table {table_ref} already exists")
        except NotFound:
            bq_schema = [bigquery.SchemaField(field['name'], field['type'], mode=field['mode']) 
                        for field in schema]
            
            table = bigquery.Table(table_ref, schema=bq_schema)
            table = self.client.create_table(table)
            logger.info(f"Created table {table_ref}")
    
    def insert_records(self, dataset_id: str, table_id: str, records: List[Dict], field_mappings: Dict = None) -> bool:
        """Insert records into BigQuery table"""
        if not records:
            return True
        
        table_ref = f"{self.project_id}.{dataset_id}.{table_id}"
        table = self.client.get_table(table_ref)
        
        # Transform records if field mappings provided
        if field_mappings:
            transformed_records = []
            for record in records:
                transformed = {}
                for zoho_field, bq_field in field_mappings.items():
                    value = record.get(zoho_field)
                    if value is not None:
                        if isinstance(value, (dict, list)):
                            transformed[bq_field] = json.dumps(value)
                        else:
                            transformed[bq_field] = str(value)
                    else:
                        transformed[bq_field] = None
                
                # Add metadata
                transformed['sync_timestamp'] = datetime.utcnow().isoformat()
                transformed['sync_source'] = 'main_autosync'
                transformed_records.append(transformed)
            
            records = transformed_records
        
        # Insert records
        errors = self.client.insert_rows_json(table, records)
        
        if errors:
            logger.error(f"Errors inserting data: {errors}")
            return False
        else:
            logger.info(f"Successfully inserted {len(records)} records into {table_ref}")
            return True

class SyncStateManager:
    """Manage sync state for all modules"""
    
    def __init__(self, state_file: str = 'main_sync_state.json'):
        self.state_file = state_file
    
    def load_state(self) -> Dict[str, Any]:
        """Load sync state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load sync state: {e}")
        
        return {
            'leads': {'last_sync': None, 'status': 'never_run'},
            'deals': {'last_sync': None, 'status': 'never_run'},
            'deals_complete': {'last_sync': None, 'status': 'never_run'},
            'last_full_sync': None
        }
    
    def save_state(self, module: str, status: str, last_sync: Optional[str] = None):
        """Save sync state for a module"""
        try:
            state = self.load_state()
            
            if last_sync is None:
                last_sync = datetime.utcnow().isoformat()
            
            state[module] = {
                'last_sync': last_sync,
                'status': status,
                'last_sync_readable': datetime.fromisoformat(last_sync.replace('Z', '')).strftime('%Y-%m-%d %H:%M:%S UTC')
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.warning(f"Could not save sync state: {e}")
    
    def get_last_sync_time(self, module: str) -> Optional[datetime]:
        """Get last sync time for a module"""
        state = self.load_state()
        last_sync = state.get(module, {}).get('last_sync')
        
        if last_sync:
            try:
                return datetime.fromisoformat(last_sync.replace('Z', ''))
            except:
                pass
        
        # Default to 24 hours ago
        return datetime.utcnow() - timedelta(hours=24)

class MainAutoSync:
    """Main coordinator for all Zoho CRM to BigQuery sync operations"""
    
    def __init__(self, sync_leads: bool = True, sync_deals: bool = True, sync_deals_complete: bool = True):
        self.sync_leads = sync_leads
        self.sync_deals = sync_deals
        self.sync_deals_complete = sync_deals_complete
        
        # Initialize clients
        try:
            self.zoho_client = ZohoCRMClient()
            self.bigquery_client = BigQueryClient()
            self.state_manager = SyncStateManager()
                
            logger.info("All clients initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize clients: {e}")
            raise
        
        # Ensure datasets and tables exist
        self._setup_bigquery_resources()
    
    def _setup_bigquery_resources(self):
        """Setup BigQuery datasets and tables"""
        try:
            # Setup for leads
            if self.sync_leads:
                dataset_id = os.getenv('BIGQUERY_DATASET_ID', 'zoho_crm')
                self.bigquery_client.ensure_dataset_exists(dataset_id)
                self.bigquery_client.ensure_table_exists(dataset_id, 'zoho_leads', LEADS_BIGQUERY_SCHEMA)
            
            # Setup for deals
            if self.sync_deals:
                self.bigquery_client.ensure_dataset_exists(DEALS_CONFIG['dataset_id'])
                self.bigquery_client.ensure_table_exists(DEALS_CONFIG['dataset_id'], DEALS_CONFIG['table_id'], DEALS_BIGQUERY_SCHEMA)
            
            # Setup for deals complete
            if self.sync_deals_complete:
                self.bigquery_client.ensure_dataset_exists(DEALS_COMPLETE_CONFIG['dataset_id'])
                # For deals complete, we'll use the same schema as deals for now
                self.bigquery_client.ensure_table_exists(DEALS_COMPLETE_CONFIG['dataset_id'], DEALS_COMPLETE_CONFIG['table_id'], DEALS_BIGQUERY_SCHEMA)
                
        except Exception as e:
            logger.error(f"Failed to setup BigQuery resources: {e}")
    
    def sync_leads_data(self) -> bool:
        """Sync leads data"""
        if not self.sync_leads:
            return True
        
        try:
            logger.info("LEADS: Starting leads sync...")
            
            # Get last sync time
            last_sync_time = self.state_manager.get_last_sync_time('leads')
            
            # Fetch new/updated leads
            leads = self.zoho_client.get_all_records('Leads', last_sync_time)
            
            if not leads:
                logger.info("LEADS: No new leads to sync")
                self.state_manager.save_state('leads', 'success')
                return True
            
            # Insert into BigQuery with field mappings
            dataset_id = os.getenv('BIGQUERY_DATASET_ID', 'zoho_crm')
            table_id = os.getenv('BIGQUERY_TABLE_ID', 'zoho_leads')
            
            success = self.bigquery_client.insert_records(dataset_id, table_id, leads, LEADS_FIELD_MAPPINGS)
            
            if success:
                self.state_manager.save_state('leads', 'success')
                logger.info(f"LEADS: Successfully synced {len(leads)} leads")
                return True
            else:
                self.state_manager.save_state('leads', 'failed')
                return False
                
        except Exception as e:
            logger.error(f"LEADS: Sync failed: {e}")
            logger.error(traceback.format_exc())
            self.state_manager.save_state('leads', 'failed')
            return False
    
    def sync_deals_data(self) -> bool:
        """Sync deals data"""
        if not self.sync_deals:
            return True
        
        try:
            logger.info("DEALS: Starting deals sync...")
            
            # Get last sync time
            last_sync_time = self.state_manager.get_last_sync_time('deals')
            
            # Fetch new/updated deals
            deals = self.zoho_client.get_all_records('Deals', last_sync_time, DEALS_BATCH_CONFIG['batch_size'])
            
            if not deals:
                logger.info("DEALS: No new deals to sync")
                self.state_manager.save_state('deals', 'success')
                return True
            
            # Insert into BigQuery with field mappings
            success = self.bigquery_client.insert_records(
                DEALS_CONFIG['dataset_id'], 
                DEALS_CONFIG['table_id'], 
                deals, 
                DEALS_FIELD_MAPPINGS
            )
            
            if success:
                self.state_manager.save_state('deals', 'success')
                logger.info(f"DEALS: Successfully synced {len(deals)} deals")
                return True
            else:
                self.state_manager.save_state('deals', 'failed')
                return False
                
        except Exception as e:
            logger.error(f"DEALS: Sync failed: {e}")
            logger.error(traceback.format_exc())
            self.state_manager.save_state('deals', 'failed')
            return False
    
    def sync_deals_complete_data(self) -> bool:
        """Sync deals complete data"""
        if not self.sync_deals_complete:
            return True
        
        try:
            logger.info("DEALS_COMPLETE: Starting deals complete sync...")
            
            # Get last sync time
            last_sync_time = self.state_manager.get_last_sync_time('deals_complete')
            
            # Fetch new/updated deals
            deals = self.zoho_client.get_all_records('Deals', last_sync_time, DEALS_COMPLETE_BATCH_CONFIG['batch_size'])
            
            if not deals:
                logger.info("DEALS_COMPLETE: No new deals to sync")
                self.state_manager.save_state('deals_complete', 'success')
                return True
            
            # Insert into BigQuery with field mappings
            success = self.bigquery_client.insert_records(
                DEALS_COMPLETE_CONFIG['dataset_id'], 
                DEALS_COMPLETE_CONFIG['table_id'], 
                deals, 
                COMPLETE_DEALS_FIELD_MAPPINGS
            )
            
            if success:
                self.state_manager.save_state('deals_complete', 'success')
                logger.info(f"DEALS_COMPLETE: Successfully synced {len(deals)} deals")
                return True
            else:
                self.state_manager.save_state('deals_complete', 'failed')
                return False
                
        except Exception as e:
            logger.error(f"DEALS_COMPLETE: Sync failed: {e}")
            logger.error(traceback.format_exc())
            self.state_manager.save_state('deals_complete', 'failed')
            return False
    
    def run_full_sync(self) -> Dict[str, bool]:
        """Run a complete sync of all enabled modules"""
        logger.info("MAIN: Starting full sync cycle")
        logger.info("=" * 80)
        
        start_time = datetime.utcnow()
        results = {}
        
        # Sync in order: leads, deals, deals_complete
        if self.sync_leads:
            results['leads'] = self.sync_leads_data()
        
        if self.sync_deals:
            results['deals'] = self.sync_deals_data()
        
        if self.sync_deals_complete:
            results['deals_complete'] = self.sync_deals_complete_data()
        
        # Log summary
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info("=" * 80)
        logger.info("MAIN: Full sync cycle completed")
        logger.info(f"DURATION: {duration:.1f} seconds")
        
        success_count = sum(1 for success in results.values() if success)
        total_count = len(results)
        
        logger.info(f"RESULTS: {success_count}/{total_count} modules synced successfully")
        
        for module, success in results.items():
            status = "SUCCESS" if success else "FAILED"
            logger.info(f"   • {module.upper()}: {status}")
        
        logger.info("=" * 80)
        
        return results
    
    def show_status(self):
        """Show current sync status"""
        state = self.state_manager.load_state()
        
        print("\nZOHO CRM TO BIGQUERY SYNC STATUS")
        print("=" * 50)
        
        for module in ['leads', 'deals', 'deals_complete']:
            if getattr(self, f'sync_{module}', False):
                module_state = state.get(module, {})
                status = module_state.get('status', 'never_run')
                last_sync = module_state.get('last_sync_readable', 'Never')
                
                print(f"{module.upper():<15}: {status.upper():<10} | Last: {last_sync}")
            else:
                print(f"{module.upper():<15}: DISABLED")
        
        print("=" * 50)
        
        if state.get('last_full_sync'):
            last_full = datetime.fromisoformat(state['last_full_sync'].replace('Z', '')).strftime('%Y-%m-%d %H:%M:%S UTC')
            print(f"Last full sync: {last_full}")
        else:
            print("Last full sync: Never")
        
        print()

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='Zoho CRM to BigQuery Main AutoSync')
    parser.add_argument('--mode', choices=['once', 'schedule', 'status'], default='schedule',
                       help='Run mode: once (single run), schedule (continuous), status (show status)')
    parser.add_argument('--leads', action='store_true', default=True, help='Enable leads sync')
    parser.add_argument('--deals', action='store_true', default=True, help='Enable deals sync')
    parser.add_argument('--deals-complete', action='store_true', default=True, help='Enable deals complete sync')
    parser.add_argument('--no-leads', action='store_true', help='Disable leads sync')
    parser.add_argument('--no-deals', action='store_true', help='Disable deals sync')
    parser.add_argument('--no-deals-complete', action='store_true', help='Disable deals complete sync')
    parser.add_argument('--interval', type=int, default=15, help='Sync interval in minutes (default: 15)')
    
    args = parser.parse_args()
    
    # Handle disable flags
    sync_leads = args.leads and not args.no_leads
    sync_deals = args.deals and not args.no_deals
    sync_deals_complete = args.deals_complete and not args.no_deals_complete
    
    # Initialize main sync
    try:
        main_sync = MainAutoSync(
            sync_leads=sync_leads,
            sync_deals=sync_deals,
            sync_deals_complete=sync_deals_complete
        )
    except Exception as e:
        logger.error(f"Failed to initialize sync system: {e}")
        sys.exit(1)
    
    if args.mode == 'status':
        main_sync.show_status()
        return
    
    print("ZOHO CRM TO BIGQUERY MAIN AUTOSYNC")
    print("=" * 50)
    print(f"Mode: {args.mode.upper()}")
    print(f"Leads sync: {'ENABLED' if sync_leads else 'DISABLED'}")
    print(f"Deals sync: {'ENABLED' if sync_deals else 'DISABLED'}")
    print(f"Deals complete sync: {'ENABLED' if sync_deals_complete else 'DISABLED'}")
    
    if args.mode == 'schedule':
        print(f"Interval: Every {args.interval} minutes")
    
    print("=" * 50)
    
    if args.mode == 'once':
        # Run once and exit
        print("Running single sync cycle...")
        results = main_sync.run_full_sync()
        
        # Exit with error code if any sync failed
        if not all(results.values()):
            sys.exit(1)
    
    elif args.mode == 'schedule':
        # Run initial sync
        print("Running initial sync...")
        main_sync.run_full_sync()
        
        # Schedule recurring syncs
        schedule.every(args.interval).minutes.do(main_sync.run_full_sync)
        
        print(f"\nScheduler started - syncing every {args.interval} minutes")
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            print("\nScheduler stopped by user")

if __name__ == "__main__":
    main()