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

# Add the scripts directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'scripts'))

app = Flask(__name__)

@app.route('/')
def home():
    """Root endpoint with service information"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Zoho CRM to BigQuery Sync</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 50px auto; 
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .status {
                color: #28a745;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }
            .info {
                background: #e9ecef;
                padding: 15px;
                border-radius: 5px;
                margin: 10px 0;
            }
            .endpoint {
                background: #007bff;
                color: white;
                padding: 8px 15px;
                border-radius: 5px;
                text-decoration: none;
                display: inline-block;
                margin: 5px;
            }
            .endpoint:hover {
                background: #0056b3;
                color: white;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 Zoho CRM to BigQuery Sync</h1>
            <div class="status">✅ Your app is working fine!</div>
            
            <div class="info">
                <strong>Service Status:</strong> Running<br>
                <strong>Timestamp:</strong> """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC") + """<br>
                <strong>Version:</strong> 1.0.0
            </div>
            
            <h3>Available Endpoints:</h3>
            <a href="/health" class="endpoint">Health Check</a>
            <a href="/status" class="endpoint">Sync Status</a>
            
            <div class="info">
                <strong>Manual Sync:</strong> POST to /sync<br>
                <strong>Project:</strong> """ + os.environ.get('GOOGLE_CLOUD_PROJECT_ID', 'not-set') + """<br>
                <strong>Dataset:</strong> """ + os.environ.get('BIGQUERY_DATASET_ID', 'not-set') + """
            </div>
            
            <p><em>This service automatically syncs Zoho CRM data to BigQuery every hour.</em></p>
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

if __name__ == '__main__':
    # Get port from environment variable (Cloud Run sets this)
    port = int(os.environ.get('PORT', 8080))
    
    # Run the Flask app
    app.run(host='0.0.0.0', port=port, debug=False)