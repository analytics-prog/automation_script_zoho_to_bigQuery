#!/usr/bin/env python3
"""
Health Check and Web Interface for Zoho CRM to BigQuery Sync
Provides HTTP endpoints for Cloud Run deployment
"""

import os
import sys
import json
import subprocess
from flask import Flask, request, jsonify
from datetime import datetime
from google.cloud import bigquery
import requests

# Add the scripts directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

app = Flask(__name__)

def get_zoho_leads_count():
    """Get count of leads from Zoho CRM"""
    try:
        # Check if required environment variables are set
        required_vars = ['ZOHO_CLIENT_ID', 'ZOHO_CLIENT_SECRET', 'ZOHO_REFRESH_TOKEN']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            return f"Missing env vars: {', '.join(missing_vars)}"
        
        # Import Zoho configuration
        sys.path.append('config')
        from config import ZOHO_CONFIG
        
        # Get access token
        token_url = "https://accounts.zoho.com.au/oauth/v2/token"
        token_data = {
            'refresh_token': os.environ.get('ZOHO_REFRESH_TOKEN'),
            'client_id': os.environ.get('ZOHO_CLIENT_ID'),
            'client_secret': os.environ.get('ZOHO_CLIENT_SECRET'),
            'grant_type': 'refresh_token'
        }
        
        token_response = requests.post(token_url, data=token_data)
        if token_response.status_code == 200:
            access_token = token_response.json().get('access_token')
            
            # Get leads count from Zoho
            headers = {
                'Authorization': f'Zoho-oauthtoken {access_token}',
                'Content-Type': 'application/json'
            }
            
            # Get total count using coql
            coql_url = "https://www.zohoapis.com.au/crm/v2/coql"
            coql_query = {
                "select_query": "SELECT COUNT(*) FROM Leads"
            }
            
            response = requests.post(coql_url, headers=headers, json=coql_query)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and len(data['data']) > 0:
                    return data['data'][0].get('count', 0)
            
            # Fallback: Get leads with pagination info
            leads_url = "https://www.zohoapis.com.au/crm/v2/Leads"
            params = {'per_page': 1, 'page': 1}
            response = requests.get(leads_url, headers=headers, params=params)
            
            if response.status_code == 200:
                data = response.json()
                info = data.get('info', {})
                return info.get('count', 0)
        
        return "Error: Unable to fetch"
        
    except ImportError as e:
        return f"Config error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

def get_bigquery_leads_count():
    """Get count of leads from BigQuery"""
    try:
        # Check if required environment variables are set
        project_id = os.environ.get('BIGQUERY_PROJECT_ID') or os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
        if not project_id:
            return "Missing: BIGQUERY_PROJECT_ID"
        
        from google.cloud import bigquery
        
        dataset_id = os.environ.get('BIGQUERY_DATASET_ID', 'zoho_crm_data')
        table_id = os.environ.get('BIGQUERY_TABLE_ID', 'leads')
        
        client = bigquery.Client(project=project_id)
        
        query = f"""
        SELECT COUNT(*) as count
        FROM `{project_id}.{dataset_id}.{table_id}`
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        for row in results:
            return row.count
            
        return 0
    except Exception as e:
        return f"Error: {str(e)}"

def get_bigquery_deals_count():
    """Get count of deals from BigQuery"""
    try:
        # Check if required environment variables are set
        project_id = os.environ.get('BIGQUERY_PROJECT_ID') or os.environ.get('GOOGLE_CLOUD_PROJECT_ID')
        if not project_id:
            return "Missing: BIGQUERY_PROJECT_ID"
        
        from google.cloud import bigquery
        
        dataset_id = os.environ.get('BIGQUERY_DATASET_ID', 'zoho_crm_data')
        
        client = bigquery.Client(project=project_id)
        
        query = f"""
        SELECT COUNT(*) as count
        FROM `{project_id}.{dataset_id}.deals`
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        for row in results:
            return row.count
            
        return 0
    except Exception as e:
        return f"Error: {str(e)}"

def get_zoho_deals_count():
    """Get count of deals from Zoho CRM"""
    try:
        # Check if required environment variables are set
        required_vars = ['ZOHO_CLIENT_ID', 'ZOHO_CLIENT_SECRET', 'ZOHO_REFRESH_TOKEN']
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            return f"Missing env vars: {', '.join(missing_vars)}"
        
        from config.config import ZOHO_FIELD_MAPPINGS
        from scripts.zoho_to_bigquery import ZohoCRMClient
        
        client = ZohoCRMClient()
        # Note: You'll need to implement get_all_deals method in ZohoCRMClient
        # For now, return a placeholder
        return "N/A (not implemented)"
    except ImportError as e:
        return f"Config error: {str(e)}"
    except Exception as e:
        return f"Error: {str(e)}"

@app.route('/')
def home():
    """Root endpoint with service information and dashboard"""
    # Check if environment is properly configured
    required_env_vars = [
        'ZOHO_CLIENT_ID', 'ZOHO_CLIENT_SECRET', 'ZOHO_REFRESH_TOKEN',
        'BIGQUERY_PROJECT_ID', 'BIGQUERY_DATASET_ID'
    ]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
    
    # Get live data counts
    zoho_leads = get_zoho_leads_count()
    bigquery_leads = get_bigquery_leads_count()
    zoho_deals = get_zoho_deals_count()
    bigquery_deals = get_bigquery_deals_count()
    
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zoho CRM to BigQuery Sync Dashboard</title>
        <style>
            body {{ 
                font-family: Arial, sans-serif; 
                max-width: 1200px; 
                margin: 20px auto; 
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }}
            .status {{
                color: #28a745;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }}
            .dashboard {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 20px 0;
            }}
            .card {{
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                border-radius: 10px;
                text-align: center;
                box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            }}
            .card.zoho {{
                background: linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%);
            }}
            .card.bigquery {{
                background: linear-gradient(135deg, #4285f4 0%, #1a73e8 100%);
            }}
            .card h3 {{
                margin: 0 0 10px 0;
                font-size: 18px;
            }}
            .card .count {{
                font-size: 36px;
                font-weight: bold;
                margin: 10px 0;
            }}
            .card .label {{
                font-size: 14px;
                opacity: 0.9;
            }}
            .sync-status {{
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 20px;
                margin: 20px 0;
            }}
            .sync-card {{
                background: #f8f9fa;
                border: 2px solid #e9ecef;
                padding: 15px;
                border-radius: 8px;
                text-align: center;
            }}
            .sync-card.synced {{
                border-color: #28a745;
                background: #d4edda;
            }}
            .sync-card.pending {{
                border-color: #ffc107;
                background: #fff3cd;
            }}
            .info {{
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }}
            .endpoint {{
                background: #007bff;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
                margin: 5px;
            }}
            .endpoint:hover {{
                background: #0056b3;
                color: white;
                text-decoration: none;
            }}
            .refresh-btn {{
                background: #28a745;
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px 0;
            }}
            .refresh-btn:hover {{
                background: #218838;
            }}
        </style>
        <script>
            function refreshPage() {{
                location.reload();
            }}
            
            // Auto-refresh every 30 seconds
            setTimeout(function() {{
                location.reload();
            }}, 30000);
        </script>
    </head>
    <body>
        <div class="container">
            <h1>📊 Zoho CRM to BigQuery Sync Dashboard</h1>
            <div class="status">✅ Your app is working fine!</div>
            
            <button class="refresh-btn" onclick="refreshPage()">🔄 Refresh Data</button>
             
             {f'''
             <div class="container" style="background: #fff3cd; border: 2px solid #ffc107; margin: 20px 0;">
                 <h2>⚠️ Setup Required</h2>
                 <p><strong>Missing Environment Variables:</strong> {", ".join(missing_vars)}</p>
                 <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0;">
                     <h4>📋 Setup Instructions:</h4>
                     <ol>
                         <li><strong>Create .env file:</strong> Copy <code>.env.example</code> to <code>.env</code></li>
                         <li><strong>Zoho CRM Setup:</strong>
                             <ul>
                                 <li>Go to <a href="https://api-console.zoho.com/" target="_blank">Zoho API Console</a></li>
                                 <li>Create a new application and get Client ID & Secret</li>
                                 <li>Generate a refresh token for your application</li>
                             </ul>
                         </li>
                         <li><strong>Google Cloud Setup:</strong>
                             <ul>
                                 <li>Create a Google Cloud Project</li>
                                 <li>Enable BigQuery API</li>
                                 <li>Create a service account and download the JSON key</li>
                                 <li>Set GOOGLE_APPLICATION_CREDENTIALS to the key file path</li>
                             </ul>
                         </li>
                         <li><strong>Update .env file</strong> with your credentials</li>
                         <li><strong>Restart the application</strong></li>
                     </ol>
                 </div>
             </div>
             ''' if missing_vars else ''}
             
             <h2>📈 Data Overview</h2>
            <div class="dashboard">
                <div class="card zoho">
                    <h3>🔴 Zoho CRM Leads</h3>
                    <div class="count">{zoho_leads}</div>
                    <div class="label">Total leads in Zoho CRM</div>
                </div>
                
                <div class="card bigquery">
                    <h3>🔵 BigQuery Leads</h3>
                    <div class="count">{bigquery_leads}</div>
                    <div class="label">Synced leads in BigQuery</div>
                </div>
                
                <div class="card zoho">
                    <h3>🔴 Zoho CRM Deals</h3>
                    <div class="count">{zoho_deals}</div>
                    <div class="label">Total deals in Zoho CRM</div>
                </div>
                
                <div class="card bigquery">
                    <h3>🔵 BigQuery Deals</h3>
                    <div class="count">{bigquery_deals}</div>
                    <div class="label">Synced deals in BigQuery</div>
                </div>
            </div>
            
            <h2>🔄 Sync Status</h2>
            <div class="sync-status">
                <div class="sync-card {'synced' if str(zoho_leads) == str(bigquery_leads) else 'pending'}">
                    <h4>Leads Sync</h4>
                    <p>{'✅ In Sync' if str(zoho_leads) == str(bigquery_leads) else '⚠️ Needs Sync'}</p>
                </div>
                <div class="sync-card {'synced' if str(zoho_deals) == str(bigquery_deals) else 'pending'}">
                    <h4>Deals Sync</h4>
                    <p>{'✅ In Sync' if str(zoho_deals) == str(bigquery_deals) else '⚠️ Needs Sync'}</p>
                </div>
            </div>
            
            <div class="info">
                <strong>Service Status:</strong> Running<br>
                <strong>Last Updated:</strong> {datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")}<br>
                <strong>Project:</strong> {os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'not-set')}<br>
                <strong>Dataset:</strong> {os.environ.get('BIGQUERY_DATASET_ID', 'not-set')}
            </div>
            
            <h3>🔧 Actions</h3>
            <a href="/health" class="endpoint">Health Check</a>
            <a href="/status" class="endpoint">Sync Status</a>
            <a href="/dashboard" class="endpoint">API Dashboard</a>
            
            <p><em>📅 This service automatically syncs Zoho CRM data to BigQuery every hour. Page auto-refreshes every 30 seconds.</em></p>
        </div>
    </body>
    </html>
    """

@app.route('/health')
def health_check():
    """Health check endpoint for Cloud Run"""
    try:
        return jsonify({
            "status": "healthy",
            "service": "zoho-bigquery-sync",
            "timestamp": datetime.now().isoformat(),
            "environment": {
                "python_version": sys.version,
                "project_id": os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'not-set'),
                "dataset_id": os.environ.get('BIGQUERY_DATASET_ID', 'not-set')
            }
        }), 200
    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }), 500

@app.route('/sync', methods=['POST'])
def trigger_sync():
    """Trigger manual sync"""
    try:
        data = request.get_json() or {}
        mode = data.get('mode', 'once')
        
        # Import and run the sync
        from main_autosync import main
        
        # Capture the output
        import io
        from contextlib import redirect_stdout, redirect_stderr
        
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Run the sync with the specified mode
                sys.argv = ['main_autosync.py', '--mode', mode]
                main()
            
            stdout_output = stdout_capture.getvalue()
            stderr_output = stderr_capture.getvalue()
            
            return jsonify({
                "status": "success",
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "output": stdout_output,
                "errors": stderr_output if stderr_output else None
            }), 200
            
        except Exception as sync_error:
            return jsonify({
                "status": "error",
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "error": str(sync_error),
                "output": stdout_capture.getvalue(),
                "errors": stderr_capture.getvalue()
            }), 500
            
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@app.route('/status')
def get_status():
    """Get current sync status"""
    try:
        # Check if log files exist and get recent entries
        log_files = [
            'logs/main_autosync.log',
            'main_autosync.log',
            'sync.log'
        ]
        
        recent_logs = []
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()
                        recent_logs.extend(lines[-10:])  # Last 10 lines
                    break
                except:
                    continue
        
        return jsonify({
            "status": "active",
            "timestamp": datetime.now().isoformat(),
            "recent_logs": recent_logs[-5:] if recent_logs else ["No recent logs found"],
            "environment": {
                "project_id": os.environ.get('GOOGLE_CLOUD_PROJECT_ID'),
                "dataset_id": os.environ.get('BIGQUERY_DATASET_ID'),
                "table_id": os.environ.get('BIGQUERY_TABLE_ID')
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }), 500

@app.route('/dashboard')
def dashboard():
    """Dashboard API endpoint with live data counts"""
    try:
        # Get live data counts
        zoho_leads = get_zoho_leads_count()
        bigquery_leads = get_bigquery_leads_count()
        zoho_deals = get_zoho_deals_count()
        bigquery_deals = get_bigquery_deals_count()
        
        return jsonify({
            'status': 'success',
            'timestamp': datetime.now().isoformat(),
            'data': {
                'zoho_crm': {
                    'leads': zoho_leads,
                    'deals': zoho_deals,
                    'total_records': zoho_leads + zoho_deals
                },
                'bigquery': {
                    'leads': bigquery_leads,
                    'deals': bigquery_deals,
                    'total_records': bigquery_leads + bigquery_deals
                },
                'sync_status': {
                    'leads_in_sync': str(zoho_leads) == str(bigquery_leads),
                    'deals_in_sync': str(zoho_deals) == str(bigquery_deals),
                    'overall_sync': str(zoho_leads) == str(bigquery_leads) and str(zoho_deals) == str(bigquery_deals)
                }
            },
            'project_info': {
                'project_id': os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'not-set'),
                'dataset_id': os.environ.get('BIGQUERY_DATASET_ID', 'not-set')
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Get port from environment variable (Cloud Run sets this)
    port = int(os.environ.get('PORT', 8080))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)