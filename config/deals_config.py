"""
Configuration for Zoho CRM Deals to BigQuery sync
"""

# Zoho CRM to BigQuery field mappings for Deals
DEALS_FIELD_MAPPINGS = {
    # Standard Zoho CRM Deals fields
    'id': 'deal_id',
    'Deal_Name': 'deal_name',
    'Owner': 'owner',
    'Account_Name': 'account_name',
    'Stage': 'stage',
    'Amount': 'amount',
    'Closing_Date': 'closing_date',
    'Probability': 'probability',
    'Type': 'deal_type',
    'Lead_Source': 'lead_source',
    'Next_Step': 'next_step',
    'Description': 'description',
    'Campaign_Source': 'campaign_source',
    'Contact_Name': 'contact_name',
    'Created_Time': 'created_time',
    'Modified_Time': 'modified_time',
    'Created_By': 'created_by',
    'Modified_By': 'modified_by',
    'Tag': 'tags',
    
    # Custom fields (based on your analysis)
    'First_Name': 'first_name',
    'Last_Name': 'last_name',
    'Email': 'email',
    'Phone': 'phone',
    'Mobile': 'mobile',
    'Date_of_Birth': 'date_of_birth',
    'Age': 'age',
    'Gender': 'gender',
    'Marital_Status': 'marital_status',
    'State': 'state',
    'Postcode': 'postcode',
    'Country': 'country',
    'Nationality': 'nationality',
    'VIsa_Type': 'visa_type',
    'English_Level': 'english_level',
    'Highest_Qualification': 'highest_qualification',
    'Course_Interested': 'course_interested',
    'Course_Level': 'course_level',
    'Course_Duration': 'course_duration',
    'Course_Fees': 'course_fees',
    'Preferred_Start_Date': 'preferred_start_date',
    'Preferred_Location': 'preferred_location',
    'How_did_you_hear_about_us': 'how_did_you_hear_about_us',
    'EOI_Source': 'eoi_source',
    'Enter_Source_If_Others_is_Selected': 'source_if_others',
    'Team': 'team',
    'Sales_Person': 'sales_person',
    'Assigned_Counsellor': 'assigned_counsellor',
    'Counsellor_Name': 'counsellor_name',
    'Counsellor_Email': 'counsellor_email',
    'Counsellor_Phone': 'counsellor_phone',
    'Initial_Deposit_Received': 'initial_deposit_received',
    'Balance_Paid': 'balance_paid',
    'Final_Balance': 'final_balance',
    'RTO_Name': 'rto_name',
    'RTO_Total_Fees': 'rto_total_fees',
    'RTO_Payable_Due_Date': 'rto_payable_due_date',
    'RTO_Paid': 'rto_paid',
    'Date_of_Last_Successful_Payment': 'date_of_last_successful_payment',
    'Status_of_Last_Stripe_Debit': 'status_of_last_stripe_debit',
    'Payment_Audit_Needed': 'payment_audit_needed',
    'Terms_Conditions_Signed': 'terms_conditions_signed',
    'Is_the_Sale_Qualified': 'is_sale_qualified',
    'Reason_for_Sale_Disqualification': 'reason_for_sale_disqualification',
    'Welcome_Call_Date': 'welcome_call_date',
    'Zoom_Registered': 'zoom_registered',
    'USI_Number': 'usi_number',
    'Workplacement_Status': 'workplacement_status',
    'Email_Opt_Out': 'email_opt_out',
    'SMS_Opt_Out': 'sms_opt_out',
    'With_Referral': 'with_referral',
    'Upsell_Referral_Claim_Date': 'upsell_referral_claim_date',
    'Partner_Contact_Number': 'partner_contact_number',
    'Search_Partner_Network': 'search_partner_network',
    'REMARKS_FOR_VALIDATION': 'remarks_for_validation',
    'Validation_Status_for_Reallocation': 'validation_status_for_reallocation',
    'When_the_Lead_is_converted': 'when_lead_converted',
    'leadchain0__Social_Lead_ID': 'social_lead_id',
    'landing_page': 'landing_page',
    'utm_source': 'utm_source',
    'utm_medium': 'utm_medium',
    'utm_campaign': 'utm_campaign',
    'utm_ad': 'utm_ad',
    'utm_adset': 'utm_adset',
}

# BigQuery configuration for Deals
BIGQUERY_CONFIG = {
    'project_id': 'your-project-id',  # Will be loaded from environment
    'dataset_id': 'zoho_crm_data',
    'table_id': 'deals',
    'location': 'US'
}

# Batch processing configuration
BATCH_CONFIG = {
    'batch_size': 200,  # Number of deals to process in each batch
    'max_retries': 3,
    'retry_delay': 5,  # seconds
    'sync_interval': 900,  # 15 minutes in seconds
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'deals_sync.log'
}

# BigQuery schema for Deals table
DEALS_BIGQUERY_SCHEMA = [
    {'name': 'deal_id', 'type': 'STRING', 'mode': 'REQUIRED'},
    {'name': 'deal_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'owner', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'account_name', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'stage', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'amount', 'type': 'FLOAT', 'mode': 'NULLABLE'},
    {'name': 'closing_date', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'probability', 'type': 'INTEGER', 'mode': 'NULLABLE'},
    {'name': 'deal_type', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'lead_source', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'next_step', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'description', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'campaign_source', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'contact_name', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'created_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    {'name': 'modified_time', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    {'name': 'created_by', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'modified_by', 'type': 'JSON', 'mode': 'NULLABLE'},
    {'name': 'tags', 'type': 'JSON', 'mode': 'NULLABLE'},
    
    # Personal Information
    {'name': 'first_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'last_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'email', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'phone', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'mobile', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'date_of_birth', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'age', 'type': 'INTEGER', 'mode': 'NULLABLE'},
    {'name': 'gender', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'marital_status', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Location Information
    {'name': 'state', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'postcode', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'country', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'nationality', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'visa_type', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Education Information
    {'name': 'english_level', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'highest_qualification', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Course Information
    {'name': 'course_interested', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'course_level', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'course_duration', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'course_fees', 'type': 'FLOAT', 'mode': 'NULLABLE'},
    {'name': 'preferred_start_date', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'preferred_location', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Source Information
    {'name': 'how_did_you_hear_about_us', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'eoi_source', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'source_if_others', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Team Information
    {'name': 'team', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'sales_person', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'assigned_counsellor', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'counsellor_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'counsellor_email', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'counsellor_phone', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Payment Information
    {'name': 'initial_deposit_received', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'balance_paid', 'type': 'INTEGER', 'mode': 'NULLABLE'},
    {'name': 'final_balance', 'type': 'FLOAT', 'mode': 'NULLABLE'},
    {'name': 'rto_name', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'rto_total_fees', 'type': 'FLOAT', 'mode': 'NULLABLE'},
    {'name': 'rto_payable_due_date', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'rto_paid', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'date_of_last_successful_payment', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'status_of_last_stripe_debit', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'payment_audit_needed', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Status Information
    {'name': 'terms_conditions_signed', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'is_sale_qualified', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'reason_for_sale_disqualification', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'welcome_call_date', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'zoom_registered', 'type': 'BOOLEAN', 'mode': 'NULLABLE'},
    {'name': 'usi_number', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'workplacement_status', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Communication Preferences
    {'name': 'email_opt_out', 'type': 'BOOLEAN', 'mode': 'NULLABLE'},
    {'name': 'sms_opt_out', 'type': 'BOOLEAN', 'mode': 'NULLABLE'},
    
    # Referral Information
    {'name': 'with_referral', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'upsell_referral_claim_date', 'type': 'DATE', 'mode': 'NULLABLE'},
    {'name': 'partner_contact_number', 'type': 'INTEGER', 'mode': 'NULLABLE'},
    {'name': 'search_partner_network', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Validation Information
    {'name': 'remarks_for_validation', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'validation_status_for_reallocation', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'when_lead_converted', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    
    # Tracking Information
    {'name': 'social_lead_id', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'landing_page', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'utm_source', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'utm_medium', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'utm_campaign', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'utm_ad', 'type': 'STRING', 'mode': 'NULLABLE'},
    {'name': 'utm_adset', 'type': 'STRING', 'mode': 'NULLABLE'},
    
    # Sync metadata
    {'name': 'sync_timestamp', 'type': 'TIMESTAMP', 'mode': 'NULLABLE'},
    {'name': 'sync_batch_id', 'type': 'STRING', 'mode': 'NULLABLE'},
]