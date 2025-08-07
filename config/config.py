"""
Configuration file for Zoho CRM to BigQuery data transfer
"""

# Zoho CRM Field Mappings
# This maps Zoho CRM field names to more standardized field names
ZOHO_FIELD_MAPPINGS = {
    # Basic Lead Information
    'Lead_Name': 'lead_name',
    'Full_Name': 'lead_name',  # Alternative field name
    'Owner': 'lead_owner',
    'Lead_Source': 'lead_source',
    'Lead_Status': 'lead_status',
    'Lead_Type': 'lead_type',
    'Lead_Status_Stage': 'lead_status_stage',
    
    # Contact Information
    'Email': 'email',
    'Phone': 'phone',
    'Mobile': 'mobile',
    'Secondary_Email': 'secondary_email',
    
    # Personal Information
    'First_Name': 'first_name',
    'Last_Name': 'last_name',
    'Title': 'title',
    'Company': 'company',
    'Industry': 'industry',
    'Date_of_Birth': 'date_of_birth',
    'Visa_Type': 'visa_type',
    
    # Address Information
    'Street': 'street',
    'City': 'city',
    'State': 'state',
    'Zip_Code': 'zip_code',
    'Country': 'country',
    
    # Marketing Information
    'Search_Terms': 'search_terms',
    'utm_source': 'utm_source',
    'utm_campaign': 'utm_campaign',
    'utm_medium': 'utm_medium',
    'utm_ad': 'utm_ad',
    'utm_adset': 'utm_adset',
    'GCLID': 'gclid',
    'Ad_Network': 'ad_network',
    'Ad_Campaign_Name': 'ad_campaign_name',
    'Keyword': 'keyword',
    'Device_Type': 'device_type',
    'Cost_per_Click': 'cost_per_click',
    'Cost_per_Conversion': 'cost_per_conversion',
    
    # Course Information
    'Course_Code': 'course_code',
    'Course_Name': 'course_name',
    'Preferred_Course': 'preferred_course',
    'RPL_or_Online_Course': 'rpl_or_online_course',
    
    # Education & Experience
    'Have_you_completed_a_Bachelor_s_Degree': 'bachelor_degree_completed',
    'Completed_any_Certificate_Level_qualification': 'certificate_qualification',
    'Completed_any_Diploma_Level_Qualification': 'diploma_qualification',
    'Are_you_presently_enrolled_in_any_studies': 'currently_enrolled',
    'Total_years_of_experience_in_the_above_industries': 'work_experience_years',
    'Worked_in_a_leadership_role_in_any_of_these': 'leadership_experience',
    'Currently_or_previously_worked_in_these_sectors': 'work_sectors',
    
    # Demographics
    'Citizenship': 'citizenship',
    'Language_spoke_at_Home': 'language_at_home',
    'Proficiency_in_English': 'english_proficiency',
    'Indigenous_Status': 'indigenous_status',
    'Disability': 'disability',
    
    # System Fields
    'Created_Time': 'created_time',
    'Modified_Time': 'modified_time',
    'Created_By': 'created_by',
    'Modified_By': 'modified_by',
    'Layout': 'layout',
    
    # Scoring and Analytics
    'Visitor_Score': 'visitor_score',
    'Average_Time_Spent_Minutes': 'average_time_spent',
    'Number_Of_Chats': 'number_of_chats',
    'Days_Visited': 'days_visited',
    
    # Preferences and Flags
    'Email_Opt_Out': 'email_opt_out',
    'SMS_Opt_Out': 'sms_opt_out',
    'DO_NOT_CALL': 'do_not_call',
    'is_this_a_Test_Lead': 'is_test_lead',
    
    # Additional Fields
    'Description': 'description',
    'Description_2': 'description_2',
    'Best_time_to_call': 'best_time_to_call',
    'USI_Number': 'usi_number',
    'Social_Lead_ID': 'social_lead_id',
    'LID': 'lid',
}

# BigQuery Configuration
BIGQUERY_CONFIG = {
    'location': 'US',  # Change based on your preference
    'write_disposition': 'WRITE_APPEND',  # Options: WRITE_APPEND, WRITE_TRUNCATE, WRITE_EMPTY
    'create_disposition': 'CREATE_IF_NEEDED',
    'max_bad_records': 0,
    'ignore_unknown_values': False
}

# Batch processing configuration
BATCH_CONFIG = {
    'batch_size': 1000,  # Number of records to process at once
    'max_retries': 3,    # Maximum number of retries for failed operations
    'retry_delay': 5     # Delay between retries in seconds
}

# Logging configuration
LOGGING_CONFIG = {
    'level': 'INFO',
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    'file': 'zoho_bigquery_transfer.log'
}