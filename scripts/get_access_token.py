#!/usr/bin/env python3
"""
Get Zoho CRM Access Token using Refresh Token
"""

import os
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_access_token():
    """Get access token using refresh token"""
    refresh_token = os.getenv('ZOHO_REFRESH_TOKEN')
    client_id = os.getenv('ZOHO_CLIENT_ID')
    client_secret = os.getenv('ZOHO_CLIENT_SECRET')
    domain = os.getenv('ZOHO_DOMAIN', 'com')
    
    if not all([refresh_token, client_id, client_secret]):
        print("❌ Missing required environment variables")
        return None
    
    url = f"https://accounts.zoho.{domain}/oauth/v2/token"
    data = {
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'grant_type': 'refresh_token'
    }
    
    try:
        response = requests.post(url, data=data)
        print(f"Response status: {response.status_code}")
        print(f"Response text: {response.text}")
        
        if response.status_code == 200:
            token_data = response.json()
            print(f"Token data: {token_data}")
            if 'access_token' in token_data:
                access_token = token_data['access_token']
                print(f"✅ Access token obtained: {access_token[:20]}...")
                return access_token
            else:
                print(f"❌ No access_token in response: {token_data}")
                return None
        else:
            print(f"❌ Failed to get access token: {response.text}")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == "__main__":
    token = get_access_token()
    if token:
        print(f"\nAdd this to your .env file:")
        print(f"ZOHO_ACCESS_TOKEN={token}")