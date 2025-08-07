# Zoho CRM to BigQuery Sync Project

This project provides automated synchronization between Zoho CRM and Google BigQuery, with support for Leads, Deals, and Deals Complete data.

## Folder Structure

```
manya/
├── analysis/           # Analysis and data files
│   ├── arboreal-logic-467306-k0-4a5ff4fe08b5.json
│   ├── deals_analysis.json
│   └── sync_state.json
├── config/            # Configuration files
│   ├── config.py                    # Leads configuration
│   ├── deals_config.py             # Deals configuration
│   └── deals_complete_config.py    # Deals complete configuration
├── credentials/       # Credential files (keep secure)
├── logs/             # Log files
│   ├── deals_complete_sync.log
│   ├── deals_setup.log
│   ├── main_autosync.log
│   └── setup_deals_complete.log
├── scripts/          # Python scripts
│   ├── main_autosync.py        # Main synchronization script
│   ├── zoho_to_bigquery.py     # Legacy sync script
│   └── get_access_token.py     # Token utility script
├── .env              # Environment variables
├── requirements.txt  # Python dependencies
└── README.md        # This file
```

## Main Script Usage

The main synchronization script is located at `scripts/main_autosync.py`. It supports multiple modes:

### Status Mode
Check the current sync status:
```bash
cd scripts
python main_autosync.py --mode status
```

### One-time Sync
Run a single synchronization:
```bash
cd scripts
python main_autosync.py --mode once
```

### Scheduled Sync
Run continuous synchronization (every 15 minutes by default):
```bash
cd scripts
python main_autosync.py --mode schedule
```

You can also customize the sync interval:
```bash
cd scripts
python main_autosync.py --mode schedule --interval 30
```



## Environment Variables

Create a `.env` file in the root directory with the following variables:

```env
# Zoho CRM Configuration
ZOHO_CLIENT_ID=your_client_id
ZOHO_CLIENT_SECRET=your_client_secret
ZOHO_REFRESH_TOKEN=your_refresh_token
ZOHO_DOMAIN=com.au

# Google BigQuery Configuration
GOOGLE_APPLICATION_CREDENTIALS=path/to/your/service-account-key.json
BIGQUERY_PROJECT_ID=your_project_id


```

## Features

- **Multi-source sync**: Supports Zoho CRM (Leads, Deals, Deals Complete)
- **Incremental sync**: Only syncs new/modified records
- **Error handling**: Comprehensive logging and error recovery
- **State management**: Tracks sync status and timestamps
- **Flexible scheduling**: Supports one-time and scheduled operations
- **BigQuery integration**: Automatic table creation and schema management

## Configuration

Each data source has its own configuration file in the `config/` folder:

- `config.py`: Leads field mappings and BigQuery settings
- `deals_config.py`: Deals field mappings and BigQuery settings
- `deals_complete_config.py`: Deals complete field mappings and BigQuery settings


## Logs

All log files are stored in the `logs/` folder:

- `main_autosync.log`: Main script execution logs
- `deals_sync.log`: Deals synchronization logs
- Other module-specific log files

## Security

- Keep credential files in the `credentials/` folder secure
- Never commit `.env` files or credential files to version control
- Use proper IAM roles and permissions for BigQuery access