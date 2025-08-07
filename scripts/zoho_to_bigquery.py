import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ZohoCRMClient:
    """Client for interacting with Zoho CRM API"""
    
    def __init__(self):
        self.client_id = os.getenv('ZOHO_CLIENT_ID')
        self.client_secret = os.getenv('ZOHO_CLIENT_SECRET')
        self.refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
        self.redirect_uri = os.getenv('ZOHO_REDIRECT_URI')
        self.domain = os.getenv('ZOHO_DOMAIN', 'com')
        self.access_token = None
        self.base_url = f"https://www.zohoapis.{self.domain}/crm/v2"
        
    def get_access_token(self) -> str:
        """Get access token using refresh token"""
        url = f"https://accounts.zoho.{self.domain}/oauth/v2/token"
        
        data = {
            'refresh_token': self.refresh_token,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token'
        }
        
        response = requests.post(url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        self.access_token = token_data['access_token']
        return self.access_token
    
    def get_headers(self) -> Dict[str, str]:
        """Get headers with authorization token"""
        if not self.access_token:
            self.get_access_token()
        
        return {
            'Authorization': f'Zoho-oauthtoken {self.access_token}',
            'Content-Type': 'application/json'
        }
    
    def get_leads(self, page: int = 1, per_page: int = 200) -> Dict[str, Any]:
        """Fetch leads from Zoho CRM"""
        url = f"{self.base_url}/Leads"
        
        params = {
            'page': page,
            'per_page': per_page
        }
        
        response = requests.get(url, headers=self.get_headers(), params=params)
        response.raise_for_status()
        
        return response.json()
    
    def get_all_leads(self) -> List[Dict[str, Any]]:
        """Fetch all leads from Zoho CRM with pagination"""
        all_leads = []
        page = 1
        
        while True:
            try:
                response = self.get_leads(page=page)
                leads = response.get('data', [])
                
                if not leads:
                    break
                
                all_leads.extend(leads)
                
                # Check if there are more pages
                info = response.get('info', {})
                if not info.get('more_records', False):
                    break
                
                page += 1
                print(f"Fetched page {page-1}, total leads so far: {len(all_leads)}")
                
            except Exception as e:
                print(f"Error fetching leads on page {page}: {str(e)}")
                break
        
        return all_leads

class BigQueryClient:
    """Client for interacting with BigQuery"""
    
    def __init__(self):
        self.project_id = os.getenv('BIGQUERY_PROJECT_ID')
        self.dataset_id = os.getenv('BIGQUERY_DATASET_ID')
        self.table_id = os.getenv('BIGQUERY_TABLE_ID')
        
        # Initialize BigQuery client
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if credentials_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        self.client = bigquery.Client(project=self.project_id)
        self.table_ref = f"{self.project_id}.{self.dataset_id}.{self.table_id}"
    
    def create_dataset_if_not_exists(self):
        """Create dataset if it doesn't exist"""
        dataset_ref = self.client.dataset(self.dataset_id)
        
        try:
            self.client.get_dataset(dataset_ref)
            print(f"Dataset {self.dataset_id} already exists")
        except NotFound:
            dataset = bigquery.Dataset(dataset_ref)
            dataset.location = "US"  # Change as needed
            dataset = self.client.create_dataset(dataset)
            print(f"Created dataset {self.dataset_id}")
    
    def create_leads_table_schema(self) -> List[bigquery.SchemaField]:
        """Define the schema for the leads table based on Zoho CRM fields"""
        return [
            # Basic Lead Information
            bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
            bigquery.SchemaField("lead_name", "STRING"),
            bigquery.SchemaField("lead_owner", "STRING"),
            bigquery.SchemaField("lead_source", "STRING"),
            bigquery.SchemaField("lead_status", "STRING"),
            bigquery.SchemaField("lead_type", "STRING"),
            bigquery.SchemaField("lead_status_stage", "STRING"),
            
            # Contact Information
            bigquery.SchemaField("email", "STRING"),
            bigquery.SchemaField("phone", "STRING"),
            bigquery.SchemaField("mobile", "STRING"),
            bigquery.SchemaField("secondary_email", "STRING"),
            
            # Personal Information
            bigquery.SchemaField("first_name", "STRING"),
            bigquery.SchemaField("last_name", "STRING"),
            bigquery.SchemaField("title", "STRING"),
            bigquery.SchemaField("company", "STRING"),
            bigquery.SchemaField("industry", "STRING"),
            bigquery.SchemaField("date_of_birth", "DATE"),
            bigquery.SchemaField("visa_type", "STRING"),
            
            # Address Information
            bigquery.SchemaField("street", "STRING"),
            bigquery.SchemaField("city", "STRING"),
            bigquery.SchemaField("state", "STRING"),
            bigquery.SchemaField("zip_code", "STRING"),
            bigquery.SchemaField("country", "STRING"),
            
            # Marketing Information
            bigquery.SchemaField("search_terms", "STRING"),
            bigquery.SchemaField("utm_source", "STRING"),
            bigquery.SchemaField("utm_campaign", "STRING"),
            bigquery.SchemaField("utm_medium", "STRING"),
            bigquery.SchemaField("utm_ad", "STRING"),
            bigquery.SchemaField("utm_adset", "STRING"),
            bigquery.SchemaField("gclid", "STRING"),
            bigquery.SchemaField("ad_network", "STRING"),
            bigquery.SchemaField("ad_campaign_name", "STRING"),
            bigquery.SchemaField("keyword", "STRING"),
            bigquery.SchemaField("device_type", "STRING"),
            bigquery.SchemaField("cost_per_click", "FLOAT"),
            bigquery.SchemaField("cost_per_conversion", "FLOAT"),
            
            # Course Information
            bigquery.SchemaField("course_code", "STRING"),
            bigquery.SchemaField("course_name", "STRING"),
            bigquery.SchemaField("preferred_course", "STRING"),
            bigquery.SchemaField("rpl_or_online_course", "STRING"),
            
            # Education & Experience
            bigquery.SchemaField("bachelor_degree_completed", "STRING"),
            bigquery.SchemaField("certificate_qualification", "STRING"),
            bigquery.SchemaField("diploma_qualification", "STRING"),
            bigquery.SchemaField("currently_enrolled", "STRING"),
            bigquery.SchemaField("work_experience_years", "STRING"),
            bigquery.SchemaField("leadership_experience", "STRING"),
            bigquery.SchemaField("work_sectors", "STRING"),
            
            # Demographics
            bigquery.SchemaField("citizenship", "STRING"),
            bigquery.SchemaField("language_at_home", "STRING"),
            bigquery.SchemaField("english_proficiency", "STRING"),
            bigquery.SchemaField("indigenous_status", "STRING"),
            bigquery.SchemaField("disability", "STRING"),
            
            # System Fields
            bigquery.SchemaField("created_time", "TIMESTAMP"),
            bigquery.SchemaField("modified_time", "TIMESTAMP"),
            bigquery.SchemaField("created_by", "STRING"),
            bigquery.SchemaField("modified_by", "STRING"),
            bigquery.SchemaField("layout", "STRING"),
            
            # Scoring and Analytics
            bigquery.SchemaField("visitor_score", "INTEGER"),
            bigquery.SchemaField("average_time_spent", "FLOAT"),
            bigquery.SchemaField("number_of_chats", "INTEGER"),
            bigquery.SchemaField("days_visited", "INTEGER"),
            
            # Preferences and Flags
            bigquery.SchemaField("email_opt_out", "BOOLEAN"),
            bigquery.SchemaField("sms_opt_out", "BOOLEAN"),
            bigquery.SchemaField("do_not_call", "BOOLEAN"),
            bigquery.SchemaField("is_test_lead", "BOOLEAN"),
            
            # Additional Fields
            bigquery.SchemaField("description", "STRING"),
            bigquery.SchemaField("description_2", "STRING"),
            bigquery.SchemaField("best_time_to_call", "STRING"),
            bigquery.SchemaField("usi_number", "STRING"),
            bigquery.SchemaField("social_lead_id", "STRING"),
            bigquery.SchemaField("lid", "STRING"),
            
            # Metadata
            bigquery.SchemaField("data_extracted_at", "TIMESTAMP"),
            bigquery.SchemaField("raw_data", "STRING")  # Store original JSON for reference
        ]
    
    def create_table_if_not_exists(self):
        """Create table if it doesn't exist"""
        try:
            self.client.get_table(self.table_ref)
            print(f"Table {self.table_ref} already exists")
        except NotFound:
            schema = self.create_leads_table_schema()
            table = bigquery.Table(self.table_ref, schema=schema)
            table = self.client.create_table(table)
            print(f"Created table {self.table_ref}")
    
    def transform_lead_data(self, lead: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Zoho lead data to match BigQuery schema"""
        def safe_get(data, key, default=None):
            """Safely get value from dictionary"""
            return data.get(key, default)
        
        def parse_datetime(date_str):
            """Parse datetime string to timestamp"""
            if not date_str:
                return None
            try:
                # Handle different datetime formats from Zoho
                if 'T' in date_str:
                    return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                else:
                    return datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
            except:
                return None
        
        def parse_date(date_str):
            """Parse date string"""
            if not date_str:
                return None
            try:
                return datetime.strptime(date_str, '%Y-%m-%d').date()
            except:
                return None
        
        def parse_float(value):
            """Parse float value"""
            if value is None or value == '':
                return None
            try:
                # Remove currency symbols and convert
                if isinstance(value, str):
                    value = value.replace('AU$', '').replace('$', '').replace(',', '').strip()
                return float(value)
            except:
                return None
        
        def parse_int(value):
            """Parse integer value"""
            if value is None or value == '':
                return None
            try:
                return int(value)
            except:
                return None
        
        def parse_bool(value):
            """Parse boolean value"""
            if value is None or value == '':
                return None
            if isinstance(value, bool):
                return value
            if isinstance(value, str):
                return value.lower() in ['true', 'yes', '1', 'on']
            return bool(value)
        
        # Extract owner information
        owner_info = safe_get(lead, 'Owner', {})
        owner_name = owner_info.get('name') if isinstance(owner_info, dict) else str(owner_info) if owner_info else None
        
        # Extract created/modified by information
        created_by_info = safe_get(lead, 'Created_By', {})
        created_by = created_by_info.get('name') if isinstance(created_by_info, dict) else str(created_by_info) if created_by_info else None
        
        modified_by_info = safe_get(lead, 'Modified_By', {})
        modified_by = modified_by_info.get('name') if isinstance(modified_by_info, dict) else str(modified_by_info) if modified_by_info else None
        
        transformed_data = {
            # Basic Lead Information
            "id": safe_get(lead, 'id'),
            "lead_name": safe_get(lead, 'Lead_Name') or safe_get(lead, 'Full_Name'),
            "lead_owner": owner_name,
            "lead_source": safe_get(lead, 'Lead_Source'),
            "lead_status": safe_get(lead, 'Lead_Status'),
            "lead_type": safe_get(lead, 'Lead_Type'),
            "lead_status_stage": safe_get(lead, 'Lead_Status_Stage'),
            
            # Contact Information
            "email": safe_get(lead, 'Email'),
            "phone": safe_get(lead, 'Phone'),
            "mobile": safe_get(lead, 'Mobile'),
            "secondary_email": safe_get(lead, 'Secondary_Email'),
            
            # Personal Information
            "first_name": safe_get(lead, 'First_Name'),
            "last_name": safe_get(lead, 'Last_Name'),
            "title": safe_get(lead, 'Title'),
            "company": safe_get(lead, 'Company'),
            "industry": safe_get(lead, 'Industry'),
            "date_of_birth": parse_date(safe_get(lead, 'Date_of_Birth')),
            "visa_type": safe_get(lead, 'Visa_Type'),
            
            # Address Information
            "street": safe_get(lead, 'Street'),
            "city": safe_get(lead, 'City'),
            "state": safe_get(lead, 'State'),
            "zip_code": safe_get(lead, 'Zip_Code'),
            "country": safe_get(lead, 'Country'),
            
            # Marketing Information
            "search_terms": safe_get(lead, 'Search_Terms'),
            "utm_source": safe_get(lead, 'utm_source'),
            "utm_campaign": safe_get(lead, 'utm_campaign'),
            "utm_medium": safe_get(lead, 'utm_medium'),
            "utm_ad": safe_get(lead, 'utm_ad'),
            "utm_adset": safe_get(lead, 'utm_adset'),
            "gclid": safe_get(lead, 'GCLID'),
            "ad_network": safe_get(lead, 'Ad_Network'),
            "ad_campaign_name": safe_get(lead, 'Ad_Campaign_Name'),
            "keyword": safe_get(lead, 'Keyword'),
            "device_type": safe_get(lead, 'Device_Type'),
            "cost_per_click": parse_float(safe_get(lead, 'Cost_per_Click')),
            "cost_per_conversion": parse_float(safe_get(lead, 'Cost_per_Conversion')),
            
            # Course Information
            "course_code": safe_get(lead, 'Course_Code'),
            "course_name": safe_get(lead, 'Course_Name'),
            "preferred_course": safe_get(lead, 'Preferred_Course'),
            "rpl_or_online_course": safe_get(lead, 'RPL_or_Online_Course'),
            
            # Education & Experience
            "bachelor_degree_completed": safe_get(lead, 'Have_you_completed_a_Bachelor_s_Degree'),
            "certificate_qualification": safe_get(lead, 'Completed_any_Certificate_Level_qualification'),
            "diploma_qualification": safe_get(lead, 'Completed_any_Diploma_Level_Qualification'),
            "currently_enrolled": safe_get(lead, 'Are_you_presently_enrolled_in_any_studies'),
            "work_experience_years": safe_get(lead, 'Total_years_of_experience_in_the_above_industries'),
            "leadership_experience": safe_get(lead, 'Worked_in_a_leadership_role_in_any_of_these'),
            "work_sectors": safe_get(lead, 'Currently_or_previously_worked_in_these_sectors'),
            
            # Demographics
            "citizenship": safe_get(lead, 'Citizenship'),
            "language_at_home": safe_get(lead, 'Language_spoke_at_Home'),
            "english_proficiency": safe_get(lead, 'Proficiency_in_English'),
            "indigenous_status": safe_get(lead, 'Indigenous_Status'),
            "disability": safe_get(lead, 'Disability'),
            
            # System Fields
            "created_time": parse_datetime(safe_get(lead, 'Created_Time')),
            "modified_time": parse_datetime(safe_get(lead, 'Modified_Time')),
            "created_by": created_by,
            "modified_by": modified_by,
            "layout": safe_get(lead, 'Layout'),
            
            # Scoring and Analytics
            "visitor_score": parse_int(safe_get(lead, 'Visitor_Score')),
            "average_time_spent": parse_float(safe_get(lead, 'Average_Time_Spent_Minutes')),
            "number_of_chats": parse_int(safe_get(lead, 'Number_Of_Chats')),
            "days_visited": parse_int(safe_get(lead, 'Days_Visited')),
            
            # Preferences and Flags
            "email_opt_out": parse_bool(safe_get(lead, 'Email_Opt_Out')),
            "sms_opt_out": parse_bool(safe_get(lead, 'SMS_Opt_Out')),
            "do_not_call": parse_bool(safe_get(lead, 'DO_NOT_CALL')),
            "is_test_lead": parse_bool(safe_get(lead, 'is_this_a_Test_Lead')),
            
            # Additional Fields
            "description": safe_get(lead, 'Description'),
            "description_2": safe_get(lead, 'Description_2'),
            "best_time_to_call": safe_get(lead, 'Best_time_to_call'),
            "usi_number": safe_get(lead, 'USI_Number'),
            "social_lead_id": safe_get(lead, 'Social_Lead_ID'),
            "lid": safe_get(lead, 'LID'),
            
            # Metadata
            "data_extracted_at": datetime.utcnow(),
            "raw_data": json.dumps(lead)  # Store original data for reference
        }
        
        return transformed_data
    
    def insert_leads(self, leads_data: List[Dict[str, Any]]) -> None:
        """Insert leads data into BigQuery"""
        if not leads_data:
            print("No leads data to insert")
            return
        
        print(f"📤 Inserting {len(leads_data)} leads into BigQuery...")
        
        # Get table reference
        table = self.client.get_table(self.table_ref)
        
        # Prepare rows for insertion (same method as test script)
        rows_to_insert = []
        for lead in leads_data:
            row = self.prepare_lead_row(lead)
            rows_to_insert.append(row)
        
        # Insert rows
        errors = self.client.insert_rows_json(table, rows_to_insert)
        
        if errors:
            print(f"❌ Errors inserting data: {errors}")
            successful_inserts = len(rows_to_insert) - len(errors)
        else:
            successful_inserts = len(rows_to_insert)
            print(f"✅ Successfully inserted {successful_inserts} leads into BigQuery")
            
        return successful_inserts
    
    def prepare_lead_row(self, lead):
        """Prepare a lead record for BigQuery insertion"""
        # Convert all values to strings and handle None values
        row = {}
        for key, value in lead.items():
            # Skip system fields that start with $
            if key.startswith('$'):
                continue
                
            if value is None:
                row[key] = None
            elif isinstance(value, (dict, list)):
                row[key] = json.dumps(value)
            else:
                row[key] = str(value)
        
        # Add metadata
        row['_extracted_at'] = datetime.utcnow().isoformat()
        row['_source'] = 'zoho_crm'
        
        return row

class ZohoToBigQueryPipeline:
    """Main pipeline class to orchestrate the data transfer"""
    
    def __init__(self):
        self.zoho_client = ZohoCRMClient()
        self.bigquery_client = BigQueryClient()
    
    def run(self, batch_size: int = 1000):
        """Run the complete pipeline"""
        try:
            print("Starting Zoho CRM to BigQuery data transfer...")
            
            # Setup BigQuery
            print("Setting up BigQuery dataset and table...")
            self.bigquery_client.create_dataset_if_not_exists()
            self.bigquery_client.create_table_if_not_exists()
            
            # Fetch leads from Zoho CRM
            print("Fetching leads from Zoho CRM...")
            leads = self.zoho_client.get_all_leads()
            print(f"Fetched {len(leads)} leads from Zoho CRM")
            
            if not leads:
                print("No leads found in Zoho CRM")
                return
            
            # Process leads in batches
            print(f"Processing leads in batches of {batch_size}...")
            for i in range(0, len(leads), batch_size):
                batch = leads[i:i + batch_size]
                print(f"Processing batch {i//batch_size + 1}: {len(batch)} leads")
                
                # Insert batch into BigQuery
                self.bigquery_client.insert_leads(batch)
            
            print("Data transfer completed successfully!")
            
        except Exception as e:
            print(f"Error in pipeline: {str(e)}")
            raise

def main():
    """Main function to run the pipeline"""
    # Check if environment variables are set
    required_vars = [
        'ZOHO_CLIENT_ID', 'ZOHO_CLIENT_SECRET', 'ZOHO_REFRESH_TOKEN',
        'BIGQUERY_PROJECT_ID', 'BIGQUERY_DATASET_ID', 'BIGQUERY_TABLE_ID'
    ]
    
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    if missing_vars:
        print(f"Missing required environment variables: {', '.join(missing_vars)}")
        print("Please check your .env file and ensure all required variables are set.")
        return
    
    # Run the pipeline
    pipeline = ZohoToBigQueryPipeline()
    pipeline.run()

if __name__ == "__main__":
    main()