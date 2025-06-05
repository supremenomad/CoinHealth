#!/usr/bin/env python3
"""
Price Updater for Crypto Data
─────────────────────────────
• Automatically finds latest crypto data JSON file
• Fetches latest price data from CoinGecko API
• Updates the JSON file every 10 minutes
• Tracks price, market cap, 24h change, and 24h volume
"""

import json
import time
import glob
from datetime import datetime
import requests
from typing import Dict, List
import logging
from pathlib import Path

# Setup data directory
DATA_DIR = Path('Data')
DATA_DIR.mkdir(exist_ok=True)

# Setup logging with more detailed format
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    handlers=[
        logging.FileHandler(DATA_DIR / 'price_updater.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class PriceUpdater:
    def __init__(self):
        self.json_file = self._find_latest_json()
        self.coins = []
        self.base_url = "https://api.coingecko.com/api/v3"
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        # Mapping for special coin IDs
        self.coin_id_mapping = {
            'bnb': 'binancecoin',
            'xrp': 'ripple'
        }
        logging.info(f"Initialized PriceUpdater with file: {self.json_file}")

    def _find_latest_json(self) -> str:
        """Find the most recent crypto data JSON file"""
        try:
            json_files = list(DATA_DIR.glob('crypto_data_*.json'))
            if not json_files:
                logging.error("No crypto data JSON files found in Data directory")
                raise FileNotFoundError("No crypto data JSON files found")
            
            latest_file = max(json_files, key=lambda x: x.stat().st_mtime)
            file_time = datetime.fromtimestamp(latest_file.stat().st_mtime)
            logging.info(f"Found latest JSON file: {latest_file} (Last modified: {file_time})")
            return str(latest_file)
        except Exception as e:
            logging.error(f"Error finding latest JSON file: {e}")
            raise

    def load_existing_data(self) -> None:
        """Load existing coin data from JSON file"""
        try:
            # Check if we need to switch to a newer file
            new_latest = self._find_latest_json()
            if new_latest != self.json_file:
                logging.info(f"Switching to newer JSON file: {new_latest} (Previous: {self.json_file})")
                self.json_file = new_latest

            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.coins = json.load(f)
            logging.info(f"Successfully loaded {len(self.coins)} coins from {self.json_file}")
            logging.info(f"Coins loaded: {', '.join(coin['name'] for coin in self.coins)}")
        except Exception as e:
            logging.error(f"Error loading JSON file {self.json_file}: {e}")
            raise

    def fetch_price_data(self) -> Dict:
        """Fetch latest price data from CoinGecko API"""
        try:
            # Get all coin IDs, applying the mapping for special cases
            coin_ids = []
            for coin in self.coins:
                if coin.get('coingecko_id'):
                    # Use mapped ID if available, otherwise use the original ID
                    api_id = self.coin_id_mapping.get(coin['coingecko_id'], coin['coingecko_id'])
                    coin_ids.append(api_id)
            
            logging.info(f"Fetching price data for coins: {', '.join(coin_ids)}")
            
            # Make API request
            url = f"{self.base_url}/simple/price"
            params = {
                'ids': ','.join(coin_ids),
                'vs_currencies': 'usd',
                'include_24hr_change': 'true',
                'include_market_cap': 'true',
                'include_24hr_vol': 'true'
            }
            
            response = requests.get(url, params=params, headers=self.headers)
            response.raise_for_status()
            
            # Create reverse mapping for response processing
            reverse_mapping = {v: k for k, v in self.coin_id_mapping.items()}
            
            # Process response to map back to original IDs
            price_data = {}
            for api_id, data in response.json().items():
                # Use original ID if it was mapped, otherwise use API ID
                original_id = reverse_mapping.get(api_id, api_id)
                price_data[original_id] = data
            
            logging.info("Successfully fetched price data from CoinGecko API")
            return price_data
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching price data from CoinGecko API: {e}")
            return {}

    def update_coin_data(self, price_data: Dict) -> None:
        """Update coin data with latest price information"""
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        updated_coins = []
        
        for coin in self.coins:
            coin_id = coin.get('coingecko_id')
            if coin_id and coin_id in price_data:
                data = price_data[coin_id]
                
                # Get old values, defaulting to 0 if None
                old_price = float(coin.get('price', 0) or 0)
                old_volume = float(coin.get('volume_24h', 0) or 0)
                
                # Update with new values, defaulting to old values if None
                new_price = float(data.get('usd', old_price) or old_price)
                new_volume = float(data.get('usd_24h_vol', old_volume) or old_volume)
                new_market_cap = float(data.get('usd_market_cap', coin.get('market_cap', 0) or 0) or 0)
                new_price_change = float(data.get('usd_24h_change', coin.get('price_change_24h', 0) or 0) or 0)
                
                # Update coin data
                coin['price'] = new_price
                coin['price_change_24h'] = new_price_change
                coin['market_cap'] = new_market_cap
                coin['volume_24h'] = new_volume
                coin['last_updated'] = current_time
                
                # Calculate changes
                price_change = ((new_price - old_price) / old_price * 100) if old_price else 0
                volume_change = ((new_volume - old_volume) / old_volume * 100) if old_volume else 0
                
                logging.info(
                    f"Updated {coin['name']} ({coin_id}):\n"
                    f"  Price: ${new_price:.2f} ({price_change:+.2f}%)\n"
                    f"  24h Change: {new_price_change:.2f}%\n"
                    f"  24h Volume: ${new_volume:,.2f} ({volume_change:+.2f}%)\n"
                    f"  Market Cap: ${new_market_cap:,.2f}"
                )
                updated_coins.append(coin['name'])
        
        if updated_coins:
            logging.info(f"Successfully updated {len(updated_coins)} coins: {', '.join(updated_coins)}")
            # Save the updated data immediately after updating
            self.save_data()
        else:
            logging.warning("No coins were updated in this cycle")

    def save_data(self) -> None:
        """Save updated data back to the same JSON file"""
        try:
            backup_file = f"{self.json_file}.backup"
            # Create backup of current file
            if Path(self.json_file).exists():
                import shutil
                shutil.copy2(self.json_file, backup_file)
                logging.info(f"Created backup file: {backup_file}")
            
            with open(self.json_file, 'w', encoding='utf-8') as f:
                json.dump(self.coins, f, indent=2)
            
            file_size = Path(self.json_file).stat().st_size
            logging.info(f"Successfully saved {file_size:,} bytes to {self.json_file}")
            
            # Remove backup if save was successful
            if Path(backup_file).exists():
                Path(backup_file).unlink()
                logging.info(f"Removed backup file: {backup_file}")
        except Exception as e:
            logging.error(f"Error saving JSON file {self.json_file}: {e}")
            # Restore from backup if save failed
            if Path(backup_file).exists():
                shutil.copy2(backup_file, self.json_file)
                logging.info(f"Restored from backup file: {backup_file}")
            raise

    def run(self, interval_minutes: int = 10) -> None:
        """Run the price updater at specified interval"""
        logging.info(f"Starting price updater (interval: {interval_minutes} minutes)")
        cycle_count = 0
        
        while True:
            try:
                cycle_count += 1
                logging.info(f"\n{'='*50}\nStarting update cycle #{cycle_count}\n{'='*50}")
                
                self.load_existing_data()
                price_data = self.fetch_price_data()
                if price_data:
                    self.update_coin_data(price_data)
                else:
                    logging.warning("No price data received from API")
                
                next_update = datetime.now().timestamp() + (interval_minutes * 60)
                next_update_str = datetime.fromtimestamp(next_update).strftime("%Y-%m-%d %H:%M:%S")
                logging.info(f"Waiting {interval_minutes} minutes until next update at {next_update_str}")
                time.sleep(interval_minutes * 60)
                
            except Exception as e:
                logging.error(f"Error in update cycle #{cycle_count}: {e}")
                logging.info("Retrying in 1 minute...")
                time.sleep(60)

def main():
    updater = PriceUpdater()
    updater.run()

if __name__ == "__main__":
    main() 