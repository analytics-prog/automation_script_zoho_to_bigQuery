import os
import time
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import threading
import logging
from logging.handlers import RotatingFileHandler
import subprocess
import queue
import sys
from google.cloud import bigquery
from google.oauth2 import service_account
from dotenv import load_dotenv
import json

# Import system monitor
try:
    from system_monitor import start_monitoring, stop_monitoring, get_system_status
    SYSTEM_MONITOR_AVAILABLE = True
except ImportError:
    SYSTEM_MONITOR_AVAILABLE = False
    print("Warning: System monitor not available. Install psutil to enable system monitoring.")

app = Flask(__name__)

# Configuration
LOG_DIR = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "runner.log")
APP_LOG_FILE = os.path.join(LOG_DIR, "app.log")

# Live logs storage
live_logs = queue.Queue(maxsize=1000)
main_process = None

# Ensure logs directory exists
os.makedirs(LOG_DIR, exist_ok=True)

# Set up logging for the web app itself
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        RotatingFileHandler(APP_LOG_FILE, maxBytes=10_000_000, backupCount=5),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def capture_main_logs():
    """Capture live logs from main.py process"""
    global main_process
    try:
        # Start main.py process
        main_process = subprocess.Popen(
            [sys.executable, 'main.py'],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        # Read output line by line
        for line in iter(main_process.stdout.readline, ''):
            if line:
                line = line.strip()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"{timestamp} | MAIN | {line}"
                
                # Add to live logs queue
                try:
                    live_logs.put_nowait(log_entry)
                except queue.Full:
                    # Remove oldest log if queue is full
                    try:
                        live_logs.get_nowait()
                        live_logs.put_nowait(log_entry)
                    except queue.Empty:
                        pass
                        
        main_process.wait()
    except Exception as e:
        logger.error(f"Error capturing main.py logs: {e}")
        
def start_main_process():
    """Start main.py process in background thread"""
    thread = threading.Thread(target=capture_main_logs, daemon=True)
    thread.start()
    return thread

def read_log_file(file_path, lines=100):
    """Read the last N lines from a log file"""
    try:
        if not os.path.exists(file_path):
            return []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
            return [line.strip() for line in all_lines[-lines:]]
    except Exception as e:
        logger.error(f"Error reading log file {file_path}: {e}")
        return [f"Error reading log file: {e}"]

def get_log_files():
    """Get list of available log files"""
    log_files = []
    if os.path.exists(LOG_DIR):
        for file in os.listdir(LOG_DIR):
            if file.endswith('.log'):
                file_path = os.path.join(LOG_DIR, file)
                stat = os.stat(file_path)
                log_files.append({
                    'name': file,
                    'path': file_path,
                    'size': stat.st_size,
                    'modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                })
    return sorted(log_files, key=lambda x: x['modified'], reverse=True)

@app.route('/')
def index():
    """Main log viewer page"""
    log_files = get_log_files()
    return render_template('log_viewer.html', log_files=log_files)

@app.route('/stats')
def stats():
    return render_template('data_stats.html')

@app.route('/api/logs/<log_file>')
def get_logs(log_file):
    """API endpoint to get logs from a specific file"""
    lines = int(request.args.get('lines', 100))
    file_path = os.path.join(LOG_DIR, log_file)
    
    # Security check - ensure file is in logs directory
    if not file_path.startswith(LOG_DIR):
        return jsonify({'error': 'Invalid file path'}), 400
    
    logs = read_log_file(file_path, lines)
    return jsonify({
        'logs': logs,
        'timestamp': datetime.now().isoformat(),
        'file': log_file
    })

@app.route('/api/logs')
def get_all_logs():
    """API endpoint to get logs from all files"""
    lines = int(request.args.get('lines', 50))
    all_logs = []
    
    # Get live logs from main.py first
    live_log_list = []
    temp_queue = queue.Queue()
    
    # Extract all logs from queue without losing them
    while not live_logs.empty():
        try:
            log_entry = live_logs.get_nowait()
            live_log_list.append(log_entry)
            temp_queue.put(log_entry)
        except queue.Empty:
            break
    
    # Put logs back in queue
    while not temp_queue.empty():
        try:
            live_logs.put_nowait(temp_queue.get_nowait())
        except (queue.Empty, queue.Full):
            break
    
    # Add live logs to response
    for log_line in live_log_list[-lines//2:]:  # Take half from live logs
        all_logs.append({
            'file': 'main.py',
            'line': log_line,
            'timestamp': datetime.now().isoformat()
        })
    
    # Get logs from files
    log_files = get_log_files()
    for log_file in log_files:
        logs = read_log_file(log_file['path'], lines//2)  # Take half from file logs
        for log_line in logs:
            all_logs.append({
                'file': log_file['name'],
                'line': log_line,
                'timestamp': datetime.now().isoformat()
            })
    
    return jsonify({
        'logs': all_logs[-lines:],  # Return last N lines across all sources
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/live-logs')
def get_live_logs():
    """API endpoint to get live logs from main.py process"""
    lines = int(request.args.get('lines', 100))
    live_log_list = []
    temp_queue = queue.Queue()
    
    # Extract all logs from queue without losing them
    while not live_logs.empty():
        try:
            log_entry = live_logs.get_nowait()
            live_log_list.append(log_entry)
            temp_queue.put(log_entry)
        except queue.Empty:
            break
    
    # Put logs back in queue
    while not temp_queue.empty():
        try:
            live_logs.put_nowait(temp_queue.get_nowait())
        except (queue.Empty, queue.Full):
            break
    
    return jsonify({
        'logs': live_log_list[-lines:],
        'timestamp': datetime.now().isoformat(),
        'source': 'main.py'
    })

@app.route('/api/stats')
def get_stats():
    """API endpoint for data transfer statistics"""
    log_file_path = os.path.join(LOG_DIR, 'app.log')
    stats = {
        'tables': {},
        'summary': {
            'total_tables': 0,
            'total_rows': 0,
            'active_operations': 0,
            'success_rate': 0
        }
    }
    
    if os.path.exists(log_file_path):
        try:
            with open(log_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                
                for line in lines:
                    line = line.strip()
                    if ' | ' in line:
                        parts = line.split(' | ', 2)
                        if len(parts) >= 3:
                            message = parts[2]
                            
                            # Parse different types of operations
                            if 'Fetched page' in message and 'total so far:' in message:
                                # Zoho operations
                                import re
                                match = re.search(r'Fetched page (\d+) \| total so far: (\d+)', message)
                                if match:
                                    rows = int(match.group(2))
                                    if 'Deals' in line or 'deals' in message:
                                        stats['tables']['zoho_deals'] = {
                                            'source': 'Zoho CRM',
                                            'table': 'Deals',
                                            'rows': rows,
                                            'status': 'processing'
                                        }
                                    elif 'Leads' in line or 'leads' in message:
                                        stats['tables']['zoho_leads'] = {
                                            'source': 'Zoho CRM',
                                            'table': 'Leads',
                                            'rows': rows,
                                            'status': 'processing'
                                        }
                            
                            elif 'Uploaded' in message and 'rows to BigQuery' in message:
                                # BigQuery upload operations
                                import re
                                match = re.search(r'Uploaded (\d+) rows to BigQuery table: ([\w_]+)', message)
                                if match:
                                    rows = int(match.group(1))
                                    table_name = match.group(2)
                                    stats['tables'][f'bq_{table_name}'] = {
                                        'source': 'BigQuery',
                                        'table': table_name,
                                        'rows': rows,
                                        'status': 'success'
                                    }
                            
                            elif 'COMPLETE' in message:
                                # Mark operations as complete
                                for key in stats['tables']:
                                    if stats['tables'][key]['status'] == 'processing':
                                        if ('Zoho' in message and 'zoho' in key) or \
                                           ('Stripe' in message and 'stripe' in key):
                                            stats['tables'][key]['status'] = 'success'
                
                # Calculate summary statistics
                tables = list(stats['tables'].values())
                stats['summary']['total_tables'] = len(tables)
                stats['summary']['total_rows'] = sum(t['rows'] for t in tables)
                stats['summary']['active_operations'] = len([t for t in tables if t['status'] == 'processing'])
                
                if len(tables) > 0:
                    success_count = len([t for t in tables if t['status'] == 'success'])
                    stats['summary']['success_rate'] = round((success_count / len(tables)) * 100)
                
        except Exception as e:
            logger.error(f"Error parsing stats: {e}")
    
    return jsonify(stats)

@app.route('/api/test-bigquery')
def test_bigquery_connection():
    """Test BigQuery connection and return status"""
    try:
        # Load environment variables
        load_dotenv()
        
        project_id = os.getenv('BQ_PROJECT_ID')
        dataset_id = os.getenv('BQ_DATASET')
        credentials_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS', './credentials/arboreal-logic-467306-k0-137d44e4d27e.json')
        
        if not all([project_id, dataset_id, credentials_path]):
            return jsonify({
                'status': 'error',
                'message': 'Missing required environment variables',
                'details': {
                    'project_id': bool(project_id),
                    'dataset_id': bool(dataset_id),
                    'credentials_path': bool(credentials_path)
                }
            })
        
        # Check credentials file
        if not os.path.exists(credentials_path):
            return jsonify({
                'status': 'error',
                'message': f'Credentials file not found: {credentials_path}'
            })
        
        # Test credentials file format
        try:
            with open(credentials_path, 'r') as f:
                creds_data = json.load(f)
            
            required_fields = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
            missing_fields = [field for field in required_fields if field not in creds_data]
            
            if missing_fields:
                return jsonify({
                    'status': 'error',
                    'message': f'Invalid credentials file - missing fields: {missing_fields}'
                })
                
        except json.JSONDecodeError:
            return jsonify({
                'status': 'error',
                'message': 'Invalid JSON in credentials file'
            })
        
        # Test BigQuery connection
        credentials = service_account.Credentials.from_service_account_file(credentials_path)
        client = bigquery.Client(project=project_id, credentials=credentials)
        
        # Test basic query
        query = "SELECT 1 as test_value"
        query_job = client.query(query)
        results = query_job.result()
        
        # Test dataset access
        dataset_ref = client.dataset(dataset_id)
        dataset = client.get_dataset(dataset_ref)
        
        # Count tables
        tables = list(client.list_tables(dataset))
        
        return jsonify({
            'status': 'success',
            'message': 'BigQuery connection successful',
            'details': {
                'project_id': project_id,
                'dataset_id': dataset_id,
                'dataset_location': dataset.location,
                'table_count': len(tables),
                'client_email': creds_data.get('client_email', 'Unknown')
            }
        })
        
    except Exception as e:
        logger.error(f"BigQuery connection test failed: {e}")
        return jsonify({
            'status': 'error',
            'message': f'BigQuery connection failed: {str(e)}'
        })

@app.route('/api/system-status')
def get_system_status_api():
    """Get current system status"""
    if not SYSTEM_MONITOR_AVAILABLE:
        return jsonify({
            'status': 'unavailable',
            'message': 'System monitor not available. Install psutil to enable system monitoring.',
            'details': None
        })
    
    try:
        status = get_system_status()
        return jsonify({
            'status': 'success',
            'message': 'System status retrieved successfully',
            'details': status
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Failed to get system status: {str(e)}',
            'details': None
        })

@app.route('/api/trigger', methods=['POST'])
def trigger_action():
    data = request.get_json() or {}
    action = data.get('action')

    if action == "run_klaviyo":
        thread = threading.Thread(target=run_script, args=("fetch_klaviyo_to_bq.py",))
        thread.start()
        return jsonify({"status": "started", "message": "Klaviyo fetch started"})
        
    return jsonify({"status": "error", "message": "Unknown action"}), 400

def run_script(script_name):
    """Run a Python script and capture its output"""
    try:
        logger.info(f"Starting manual run of {script_name}")
        process = subprocess.Popen(
            [sys.executable, script_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        for line in iter(process.stdout.readline, ''):
            if line:
                line = line.strip()
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_entry = f"{timestamp} | {script_name} | {line}"
                try:
                    live_logs.put_nowait(log_entry)
                except queue.Full:
                    try:
                        live_logs.get_nowait()
                        live_logs.put_nowait(log_entry)
                    except queue.Empty:
                        pass
                        
        process.wait()
        logger.info(f"Manual run of {script_name} completed with code {process.returncode}")
        
    except Exception as e:
        logger.error(f"Error running {script_name}: {e}")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    args = parser.parse_args()

    logger.info("Starting log viewer web application...")
    
    # Start system monitoring if available
    if SYSTEM_MONITOR_AVAILABLE:
        logger.info("Starting system monitoring...")
        start_monitoring()
    
    logger.info("Starting main.py process for live log capture...")
    start_main_process()
    app.run(debug=False, host=args.host, port=args.port)