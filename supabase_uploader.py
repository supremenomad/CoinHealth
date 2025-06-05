#!/usr/bin/env python3
"""
Supabase Uploader for Crypto Data
───────────────────────────────
• Uploads JSON data to Supabase tables
• Uploads coin logos to Supabase storage
• Handles data synchronization
"""

import os
import json
from pathlib import Path
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup directories
DATA_DIR = Path('Data')
LOGO_DIR = DATA_DIR / 'Logo'

# Supabase configuration
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_KEY = os.getenv('SUPABASE_KEY')

class SupabaseUploader:
    def __init__(self):
        """Initialize Supabase client"""
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError("Supabase URL and key must be set in .env file")
        
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        self._ensure_tables_exist()
        self._ensure_storage_exists()

    def _ensure_tables_exist(self):
        """Ensure required tables exist in Supabase"""
        # This will be handled by Supabase migrations
        pass

    def _ensure_storage_exists(self):
        """Ensure required storage buckets exist"""
        try:
            # Create logos bucket if it doesn't exist
            self.supabase.storage.create_bucket('logos', {'public': True})
        except Exception as e:
            print(f"Note: Logos bucket may already exist: {e}")

    def upload_json_data(self, json_file: Path):
        """Upload JSON data to Supabase"""
        try:
            # Read JSON file
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Extract date from filename
            date_str = json_file.stem.split('_')[-1]
            
            # Upload each coin's data
            for coin in data:
                # Add upload date
                coin['uploaded_at'] = datetime.now().isoformat()
                
                # Upload to Supabase
                result = self.supabase.table('crypto_data').upsert({
                    'date': date_str,
                    'coin_data': coin
                }).execute()
                
                print(f"✅ Uploaded data for {coin['name']} ({date_str})")

        except Exception as e:
            print(f"❌ Error uploading JSON data: {e}")
            raise

    def upload_logo(self, logo_file: Path):
        """Upload a logo to Supabase storage"""
        try:
            # Get the coin ID from the filename
            coin_id = logo_file.stem
            
            # Upload file to Supabase storage
            with open(logo_file, 'rb') as f:
                self.supabase.storage.from_('logos').upload(
                    f"{coin_id}{logo_file.suffix}",
                    f.read(),
                    {'content-type': f'image/{logo_file.suffix[1:]}'}
                )
            
            print(f"✅ Uploaded logo for {coin_id}")
            
            # Get public URL
            url = self.supabase.storage.from_('logos').get_public_url(
                f"{coin_id}{logo_file.suffix}"
            )
            
            # Update coin data with logo URL
            self.supabase.table('crypto_data').update({
                'logo_url': url
            }).eq('coin_data->>coingecko_id', coin_id).execute()
            
        except Exception as e:
            print(f"❌ Error uploading logo {logo_file.name}: {e}")
            raise

    def sync_all_data(self):
        """Sync all JSON files and logos to Supabase"""
        try:
            # Upload all JSON files
            json_files = sorted(DATA_DIR.glob('crypto_data_*.json'))
            for json_file in json_files:
                print(f"\n📤 Uploading data from {json_file.name}")
                self.upload_json_data(json_file)

            # Upload all logos
            logo_files = list(LOGO_DIR.glob('*.*'))
            for logo_file in logo_files:
                print(f"\n🖼️ Uploading logo {logo_file.name}")
                self.upload_logo(logo_file)

            print("\n✅ All data synchronized successfully!")

        except Exception as e:
            print(f"❌ Error during sync: {e}")
            raise

def main():
    try:
        uploader = SupabaseUploader()
        uploader.sync_all_data()
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        raise

if __name__ == "__main__":
    main() 