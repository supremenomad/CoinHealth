#!/usr/bin/env python3
"""
Enhanced Crypto Scraper
───────────────────────
• Scrapes top N coins from CoinGecko
• Extracts Twitter followers count
• Extracts GitHub stars count
• Saves data in multiple formats (CSV, JSON, Parquet)
• Downloads and saves coin logos
"""

import re
import time
import json
import csv
import os
import pickle
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from dotenv import load_dotenv
from dateutil import parser

# Load environment variables
load_dotenv()

# Setup directories
DATA_DIR = Path('Data')
DATA_DIR.mkdir(exist_ok=True)
DEBUG_DIR = DATA_DIR / 'Debug'
DEBUG_DIR.mkdir(exist_ok=True)
LOGO_DIR = DATA_DIR / 'Logo'
LOGO_DIR.mkdir(exist_ok=True)

NUM_COINS = 150  # Number of top coins to scrape
COINS_PER_PAGE = 100  # Number of coins displayed per page
BATCH_SIZE = 5   # Number of tabs to open in parallel

def _num(txt: str) -> float:
    """Convert text to float, handling K, M, B suffixes"""
    if not txt:
        return 0.0
    txt = txt.replace(',', '').strip()
    multiplier = 1
    if txt.endswith('B'):
        multiplier = 1e9
        txt = txt[:-1]
    elif txt.endswith('M'):
        multiplier = 1e6
        txt = txt[:-1]
    elif txt.endswith('K'):
        multiplier = 1e3
        txt = txt[:-1]
    try:
        return float(txt) * multiplier
    except ValueError:
        return 0.0

def download_logo(url: str, coin_id: str) -> str:
    """Download logo and save it to the Logo directory"""
    try:
        # Get the file extension from the URL
        ext = url.split('.')[-1].lower()
        if ext not in ['png', 'jpg', 'jpeg', 'svg', 'webp']:
            ext = 'png'  # Default to png if extension is not recognized
        
        # Create filename with coin_id
        filename = f"{coin_id}.{ext}"
        filepath = LOGO_DIR / filename
        
        # Download the image
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Save the image
        with open(filepath, 'wb') as f:
            f.write(response.content)
        
        print(f"💾 Saved logo for {coin_id} to {filepath}")
        return str(filepath)
    except Exception as e:
        print(f"❌ Error downloading logo for {coin_id}: {e}")
        return None

class CryptoScraper:
    def __init__(self, headless=True):
        self.driver = self._build_driver(headless)
        self.wait = WebDriverWait(self.driver, 8)
        self.coins = []
        self.main = None
        self.current_date = datetime.now().strftime("%Y-%m-%d")
        self.last_json_data = self._load_last_json()
        self.cookies_file = DATA_DIR / "twitter_cookies.pkl"
        self._login_to_twitter()

    def _save_debug_file(self, content: str, prefix: str, coin_name: str) -> None:
        """Save debug content to a file in the Debug directory"""
        safe_name = coin_name.replace(" ", "_").replace("/", "_")
        debug_file = DEBUG_DIR / f"{prefix}_{safe_name}.html"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"📝 Saved debug file: {debug_file}")

    def _login_to_twitter(self):
        """Login to Twitter and save cookies for future sessions"""
        print("\n🔑 Logging into Twitter...")
        
        # Try to load existing cookies
        if self.cookies_file.exists():
            try:
                self.driver.get("https://twitter.com")
                cookies = pickle.load(open(self.cookies_file, "rb"))
                for cookie in cookies:
                    self.driver.add_cookie(cookie)
                print("✅ Loaded existing Twitter session")
                return
            except Exception as e:
                print(f"❌ Error loading cookies: {e}")

        # If no cookies or loading failed, perform new login
        try:
            self.driver.get("https://twitter.com/login")
            time.sleep(3)

            # Enter username
            username = os.getenv("TWITTER_USERNAME")
            password = os.getenv("TWITTER_PASSWORD")
            
            if not username or not password:
                raise ValueError("Twitter credentials not found in .env file")

            # Wait for and fill username
            username_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[autocomplete='username']"))
            )
            username_input.send_keys(username)
            
            # Click next
            next_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']"))
            )
            next_button.click()
            time.sleep(2)

            # Enter password
            password_input = self.wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='password']"))
            )
            password_input.send_keys(password)

            # Click login
            login_button = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[text()='Log in']"))
            )
            login_button.click()
            time.sleep(5)

            # Save cookies for future sessions
            pickle.dump(self.driver.get_cookies(), open(self.cookies_file, "wb"))
            print("✅ Successfully logged into Twitter and saved session")
        except Exception as e:
            print(f"❌ Error logging into Twitter: {e}")
            raise

    def _load_last_json(self):
        """Load data from the most recent JSON file if it exists"""
        try:
            # Find the most recent JSON file
            json_files = list(DATA_DIR.glob('crypto_data_*.json'))
            if not json_files:
                return None
            
            latest_json = max(json_files, key=lambda x: x.stat().st_mtime)
            print(f"📂 Loading data from {latest_json}")
            with open(latest_json, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Error loading last JSON: {e}")
            return None

    def _get_existing_data(self, coin_name):
        """Get existing data for a coin from the last JSON"""
        if self.last_json_data is None:
            return None
        
        for coin_data in self.last_json_data:
            if coin_data['name'] == coin_name:
                return coin_data
        return None

    def _build_driver(self, headless):
        """Setup Chrome driver with optimized settings"""
        o = Options()
        if headless:
            o.add_argument("--headless=new")
            o.add_argument("--window-size=1920,1080")
        o.page_load_strategy = "eager"
        o.add_argument("--no-sandbox")
        o.add_argument("--disable-dev-shm-usage")
        o.add_argument("--ignore-certificate-errors")
        o.add_argument("--ignore-ssl-errors")
        o.add_experimental_option("prefs", {
            "profile.managed_default_content_settings.images": 2,
            "profile.managed_default_content_settings.stylesheets": 2,
            "profile.managed_default_content_settings.fonts": 2,
        })
        o.add_experimental_option("excludeSwitches", ["enable-automation"])
        o.add_experimental_option("useAutomationExtension", False)
        o.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122 Safari/537.36")
        drv = webdriver.Chrome(options=o)
        drv.execute_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        return drv

    def _scroll_rows(self, n):
        """Ensure first N rows are loaded by scrolling"""
        last = 0
        while True:
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
            if len(rows) >= n:
                return rows[:n]
            self.driver.execute_script("window.scrollBy(0,700)")
            time.sleep(0.4)
            y = self.driver.execute_script("return window.pageYOffset")
            if y == last:
                return rows
            last = y

    def _navigate_to_page(self, page_num):
        """Navigate to a specific page of coins"""
        if page_num == 1:
            self.driver.get("https://www.coingecko.com/")
        else:
            self.driver.get(f"https://www.coingecko.com/?page={page_num}")
        
        # Wait for the table to load (increase timeout to 20s)
        try:
            WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "table"))
            )
        except TimeoutException:
            print("❌ Timeout: Could not find CoinGecko table. Saving page source for debugging.")
            self._save_debug_file(self.driver.page_source, "debug_coingecko_table", "page_load")
            raise
        time.sleep(2)  # Additional wait to ensure page is fully loaded

    def collect_coins(self, n=NUM_COINS):
        """Collect basic coin information from CoinGecko"""
        print(f"🌐 Collecting top {n} coins from CoinGecko...")
        
        coins_collected = 0
        current_page = 1
        
        while coins_collected < n:
            print(f"\n📄 Processing page {current_page}...")
            self._navigate_to_page(current_page)
            
            # Calculate how many coins to collect from this page
            coins_to_collect = min(COINS_PER_PAGE, n - coins_collected)
            rows = self._scroll_rows(coins_to_collect)
            print(f"📈 Found {len(rows)} coins on page {current_page}")

            for rank, row in enumerate(rows, coins_collected + 1):
                try:
                    link = row.find_element(By.CSS_SELECTOR, "td:nth-child(3) a")
                    name = link.text.strip()
                    url = link.get_attribute("href")

                    # Check if we have existing data for this coin
                    existing_data = self._get_existing_data(name)

                    try:
                        symbol = row.find_element(
                            By.CSS_SELECTOR, "td:nth-child(3) .tw-text-gray-500"
                        ).text.strip().upper()
                    except NoSuchElementException:
                        symbol = "?"

                    price = _num(row.find_element(By.CSS_SELECTOR, "td:nth-child(4)").text)
                    mc_raw = row.find_element(By.CSS_SELECTOR, "td:nth-child(9)").text
                    market_cap = _num(mc_raw)

                    # Try to get CoinGecko API ID from data attribute, fallback to URL
                    coingecko_id = None
                    try:
                        coingecko_id = row.get_attribute('data-coin-id')
                        if not coingecko_id or coingecko_id == 'null':
                            coingecko_id = None
                    except Exception:
                        coingecko_id = None
                    if not coingecko_id:
                        # fallback to URL
                        coingecko_id = url.split('/')[-1]

                    coin_data = {
                        'rank': rank,
                        'name': name,
                        'symbol': symbol,
                        'coingecko_url': url,
                        'price': price,
                        'market_cap': market_cap,
                        'twitter_handle': None,
                        'twitter_url': None,
                        'twitter_followers': None,
                        'twitter_first_tweet_date': None,
                        'github': None,
                        'github_stars': None,
                        'github_forks': None,
                        'github_last_updated': None,
                        'logo_url': None,
                        'logo_local_path': None,
                        'coingecko_id': coingecko_id,
                        'scraped_at': time.strftime("%Y-%m-%d %H:%M:%S")
                    }

                    # If we have existing data, preserve the important fields if present and not null
                    if existing_data:
                        for key in [
                            'name', 'twitter_handle', 'twitter_url', 'github',
                            'logo_url', 'logo_local_path', 'coingecko_id']:
                            if existing_data.get(key):
                                coin_data[key] = existing_data[key]
                        print(f"📎 Using existing data for {name} (preserving key fields)")
                    else:
                        print(f"🆕 New coin found: {name}")

                    # Only download logo if logo_url or logo_local_path is missing
                    if not coin_data['logo_url'] or not coin_data['logo_local_path']:
                        try:
                            logo_element = row.find_element(By.CSS_SELECTOR, "td:nth-child(3) img")
                            if logo_element:
                                logo_url = logo_element.get_attribute("src")
                                if logo_url:
                                    coin_data['logo_url'] = logo_url
                                    print(f"🖼️ Found logo for {name}: {logo_url}")
                                    if coin_data['coingecko_id']:
                                        local_path = download_logo(logo_url, coin_data['coingecko_id'])
                                        if local_path:
                                            coin_data['logo_local_path'] = local_path
                        except NoSuchElementException:
                            try:
                                self.driver.get(url)
                                time.sleep(2)
                                logo_element = self.driver.find_element(By.CSS_SELECTOR, "img.coin-logo")
                                if logo_element:
                                    logo_url = logo_element.get_attribute("src")
                                    if logo_url:
                                        coin_data['logo_url'] = logo_url
                                        print(f"🖼️ Found logo for {name} from coin page: {logo_url}")
                                        if coin_data['coingecko_id']:
                                            local_path = download_logo(logo_url, coin_data['coingecko_id'])
                                            if local_path:
                                                coin_data['logo_local_path'] = local_path
                            except Exception as e:
                                print(f"❌ Error getting logo for {name}: {e}")
                            finally:
                                self.driver.get("https://www.coingecko.com/")
                                time.sleep(2)

                    self.coins.append(coin_data)
                    print(f"✅ Added {name} ({symbol}) - Rank {rank}")
                except Exception as e:
                    print(f"❌ Error processing row {rank}: {e}")

            coins_collected += len(rows)
            current_page += 1

            # Save progress after each page
            self.save_results()

            # Add a small delay between pages
            time.sleep(2)

    def _extract_social_links(self):
        """Extract Twitter and GitHub links from coin pages"""
        print("\n🔍 Extracting social media links...")
        self.main = self.driver.current_window_handle

        for i in range(0, len(self.coins), BATCH_SIZE):
            batch = self.coins[i:i+BATCH_SIZE]
            
            # Open tabs for batch
            for coin in batch:
                # Skip if we already have both social links
                if coin["twitter_url"] and coin["github"]:
                    continue

                pre = set(self.driver.window_handles)
                self.driver.execute_script("window.open('about:blank','_blank')")
                handle = next(h for h in self.driver.window_handles if h not in pre)
                coin["_handle"] = handle
                self.driver.switch_to.window(handle)
                self.driver.get(coin["coingecko_url"])
                time.sleep(2)  # Allow page to load

            # Process each tab
            for coin in batch:
                # Skip if we already have both social links
                if coin["twitter_url"] and coin["github"]:
                    continue

                self.driver.switch_to.window(coin["_handle"])
                try:
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    # Extract Twitter
                    if not coin["twitter_url"]:
                        twitter_elements = self.driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'twitter.com') or contains(@href, 'x.com')]"
                        )
                        if twitter_elements:
                            twitter_url = twitter_elements[0].get_attribute("href")
                            coin["twitter_url"] = twitter_url
                            match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]{2,15})", twitter_url)
                            if match:
                                coin["twitter_handle"] = match.group(1)

                    # Extract GitHub only if we don't have it
                    if not coin["github"]:
                        github_elements = self.driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'github.com')]"
                        )
                        if github_elements:
                            github_url = github_elements[0].get_attribute("href")
                            coin["github"] = github_url
                            print(f"🔗 Found GitHub URL for {coin['name']}: {github_url}")

                except Exception as e:
                    print(f"❌ Error processing {coin['name']}: {e}")

            # Close tabs
            for coin in batch:
                if "_handle" in coin:
                    self.driver.switch_to.window(coin["_handle"])
                    self.driver.close()
            self.driver.switch_to.window(self.main)

    def _scrape_twitter_followers(self):
        """Scrape Twitter follower counts and first tweet date"""
        print("\n🐦 Scraping Twitter followers and first tweet date...")
        
        # Process coins in batches of 5
        for i in range(0, len(self.coins), 5):
            batch = self.coins[i:i+5]
            print(f"\n📊 Processing batch {i//5 + 1} of {(len(self.coins) + 4)//5}")
            
            # Open tabs for batch
            for coin in batch:
                if not coin["twitter_url"]:
                    continue

                try:
                    pre = set(self.driver.window_handles)
                    self.driver.execute_script("window.open('about:blank','_blank')")
                    handle = next(h for h in self.driver.window_handles if h not in pre)
                    self.driver.switch_to.window(handle)
                    self.driver.get(coin["twitter_url"])
                    time.sleep(5)
                    coin["_handle"] = handle
                except Exception as e:
                    print(f"❌ Error opening Twitter tab for {coin['name']}: {e}")
                    continue

            # Process each tab
            for coin in batch:
                if not coin["twitter_url"] or "_handle" not in coin:
                    continue

                try:
                    self.driver.switch_to.window(coin["_handle"])
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    # Extract Twitter
                    if not coin["twitter_url"]:
                        twitter_elements = self.driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'twitter.com') or contains(@href, 'x.com')]"
                        )
                        if twitter_elements:
                            twitter_url = twitter_elements[0].get_attribute("href")
                            coin["twitter_url"] = twitter_url
                            match = re.search(r"(?:twitter\.com|x\.com)/([A-Za-z0-9_]{2,15})", twitter_url)
                            if match:
                                coin["twitter_handle"] = match.group(1)

                    # Extract GitHub only if we don't have it
                    if not coin["github"]:
                        github_elements = self.driver.find_elements(
                            By.XPATH,
                            "//a[contains(@href, 'github.com')]"
                        )
                        if github_elements:
                            github_url = github_elements[0].get_attribute("href")
                            coin["github"] = github_url
                            print(f"🔗 Found GitHub URL for {coin['name']}: {github_url}")

                    # Extract tweet dates
                    tweet_dates = []
                    try:
                        tweets = self.driver.find_elements(By.CSS_SELECTOR, "article[data-testid='tweet']")
                        for tweet in tweets:
                            try:
                                # Skip if it's a pinned tweet
                                is_pinned = False
                                
                                # Check for pinned indicators
                                pinned_indicators = [
                                    "Pinned Tweet",
                                    "Pinned",
                                    "Pinned by",
                                    "Pinned Tweet by"
                                ]
                                
                                tweet_text = tweet.text
                                aria_label = tweet.get_attribute('aria-label') or ''
                                
                                # Check text and aria-label for pinned indicators
                                if any(indicator in tweet_text or indicator in aria_label for indicator in pinned_indicators):
                                    is_pinned = True
                                    print(f"📌 Found pinned tweet for {coin['name']}")
                                    continue
                                
                                # Check for socialContext span
                                pinned_label = tweet.find_elements(By.CSS_SELECTOR, "span[data-testid='socialContext']")
                                if pinned_label and any("Pinned" in label.text for label in pinned_label):
                                    is_pinned = True
                                    print(f"📌 Found pinned tweet (via socialContext) for {coin['name']}")
                                    continue
                                
                                # Find the time element with multiple selectors
                                time_element = None
                                for selector in [
                                    "time[datetime]",
                                    "a[href*='/status/'] time",
                                    "div[data-testid='tweetText'] + div time",
                                    "div[data-testid='tweetText'] ~ div time",
                                    "div[data-testid='tweetText'] + div a[href*='/status/'] time",
                                    "div[data-testid='tweetText'] ~ div a[href*='/status/'] time",
                                    "div[data-testid='tweetText'] + div a time",
                                    "div[data-testid='tweetText'] ~ div a time",
                                    "div[data-testid='tweetText'] + div div time",
                                    "div[data-testid='tweetText'] ~ div div time"
                                ]:
                                    try:
                                        time_element = tweet.find_element(By.CSS_SELECTOR, selector)
                                        if time_element:
                                            break
                                    except:
                                        continue
                                
                                if time_element:
                                    datetime_str = time_element.get_attribute("datetime")
                                    if datetime_str:
                                        tweet_dates.append(datetime_str)
                                        print(f"📅 Found tweet date for {coin['name']}: {datetime_str}")
                                    else:
                                        print(f"⚠️ Found time element but no datetime attribute for {coin['name']}")
                                        # Try to get the text content as fallback
                                        text_date = time_element.text.strip()
                                        if text_date:
                                            print(f"📅 Found text date: {text_date}")
                                            try:
                                                # Try to parse relative time (e.g., "2h", "3d", etc.)
                                                if any(unit in text_date.lower() for unit in ['h', 'd', 'm', 's']):
                                                    # Calculate the actual date based on relative time
                                                    now = datetime.now()
                                                    if 'h' in text_date.lower():
                                                        hours = int(''.join(filter(str.isdigit, text_date)))
                                                        dt = now - timedelta(hours=hours)
                                                    elif 'd' in text_date.lower():
                                                        days = int(''.join(filter(str.isdigit, text_date)))
                                                        dt = now - timedelta(days=days)
                                                    elif 'm' in text_date.lower():
                                                        minutes = int(''.join(filter(str.isdigit, text_date)))
                                                        dt = now - timedelta(minutes=minutes)
                                                    else:
                                                        dt = now
                                                    tweet_dates.append(dt.isoformat())
                                                    print(f"📅 Converted relative time to: {dt.isoformat()}")
                                            except Exception as e:
                                                print(f"❌ Error parsing relative time: {e}")
                                else:
                                    print(f"⚠️ No time element found for tweet in {coin['name']}")
                            except Exception as e:
                                print(f"❌ Error processing tweet for {coin['name']}: {e}")
                                continue
                        
                        # Get the most recent tweet date
                        if tweet_dates:
                            dt_objs = [parser.isoparse(dt) for dt in tweet_dates]
                            most_recent = max(dt_objs)
                            first_tweet_date = most_recent.strftime("%Y-%m-%d %H:%M:%S")
                            coin["twitter_first_tweet_date"] = first_tweet_date
                            print(f"📅 Most recent tweet date for {coin['name']}: {first_tweet_date}")
                        else:
                            print(f"❌ No valid non-pinned tweet found for {coin['name']}")
                            self._save_debug_file(self.driver.page_source, "debug_twitter_tweets", coin['name'])
                    except Exception as e:
                        print(f"❌ Error finding tweet date for {coin['name']}: {e}")

                    # Follower count logic
                    selectors = [
                        '[data-testid="UserFollowers"] span span',
                        '[data-testid="UserFollowers"] span',
                        'a[href$="/followers"] span span',
                        'a[href$="/verified_followers"] span span',
                        'a[href*="/followers"] span span',
                        'a[href*="/followers"] span',
                        'div[data-testid="UserFollowers"] span',
                        'div[data-testid="UserFollowers"] span span',
                        'a[href*="followers"] span span',
                        'a[href*="followers"] span',
                        'div[data-testid="UserFollowers"]',
                        'div[data-testid="UserFollowers"] a span',
                        'div[data-testid="UserFollowers"] a'
                    ]
                    followers_found = False
                    for selector in selectors:
                        try:
                            elements = WebDriverWait(self.driver, 5).until(
                                EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                            )
                            for element in elements:
                                followers_text = element.text.strip()
                                if followers_text and any(c.isdigit() for c in followers_text):
                                    num_text = re.sub(r'[^\d.KMB]', '', followers_text)
                                    if num_text:
                                        coin["twitter_followers"] = _num(num_text)
                                        print(f"✅ {coin['name']}: {coin['twitter_followers']} followers")
                                        followers_found = True
                                        break
                            if followers_found:
                                break
                        except:
                            continue
                    if not followers_found:
                        print(f"❌ Could not find followers for {coin['name']}")
                        page_source = self.driver.page_source
                        follower_patterns = [
                            r'"followers_count":(\d+)',
                            r'(\d+(?:\.\d+)?[KMB]?)\s*(?:Followers|followers)',
                            r'Followers["\s]*[>:]\s*(\d+(?:\.\d+)?[KMB]?)',
                        ]
                        for pattern in follower_patterns:
                            matches = re.findall(pattern, page_source, re.IGNORECASE)
                            if matches:
                                coin["twitter_followers"] = _num(matches[0])
                                print(f"✅ {coin['name']}: {coin['twitter_followers']} followers (from source)")
                                followers_found = True
                                break
                        if not followers_found:
                            self._save_debug_file(self.driver.page_source, "debug_twitter", coin['name'])
                    time.sleep(3)
                except Exception as e:
                    print(f"❌ Error scraping Twitter for {coin['name']}: {e}")
                finally:
                    self.driver.close()
                    self.driver.switch_to.window(self.main)

    def _scrape_github_stars(self):
        """Scrape GitHub stars, forks, and last update date"""
        print("\n⭐ Scraping GitHub stars, forks, and last update date...")
        
        # Process coins in batches of 5
        for i in range(0, len(self.coins), 5):
            batch = self.coins[i:i+5]
            print(f"\n📊 Processing batch {i//5 + 1} of {(len(self.coins) + 4)//5}")
            
            # Open tabs for batch
            for coin in batch:
                if not coin["github"]:
                    continue

                try:
                    pre = set(self.driver.window_handles)
                    self.driver.execute_script("window.open('about:blank','_blank')")
                    handle = next(h for h in self.driver.window_handles if h not in pre)
                    self.driver.switch_to.window(handle)
                    self.driver.get(coin["github"])
                    time.sleep(3)
                    coin["_handle"] = handle
                except Exception as e:
                    print(f"❌ Error opening GitHub tab for {coin['name']}: {e}")
                    continue

            # Process each tab
            for coin in batch:
                if not coin["github"] or "_handle" not in coin:
                    continue

                try:
                    # Check if window still exists
                    if coin["_handle"] not in self.driver.window_handles:
                        print(f"⚠️ Window for {coin['name']} was closed, skipping")
                        continue

                    self.driver.switch_to.window(coin["_handle"])
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                    
                    # Try to find the last update date
                    try:
                        # Look for relative-time elements
                        updated_elements = self.driver.find_elements(
                            By.CSS_SELECTOR,
                            "relative-time"
                        )
                        
                        for element in updated_elements:
                            try:
                                # First try to get the datetime attribute
                                datetime_attr = element.get_attribute("datetime")
                                if datetime_attr:
                                    # Parse the ISO format datetime
                                    try:
                                        from datetime import datetime
                                        dt = datetime.strptime(datetime_attr, "%Y-%m-%dT%H:%M:%SZ")
                                        last_updated = dt.strftime("%Y-%m-%d")
                                        coin["github_last_updated"] = last_updated
                                        print(f"📅 Found last update date for {coin['name']}: {last_updated}")
                                        break
                                    except ValueError as e:
                                        print(f"❌ Error parsing datetime for {coin['name']}: {e}")
                                        continue
                                
                                # If datetime attribute is not available, try the title attribute
                                title_attr = element.get_attribute("title")
                                if title_attr:
                                    # Extract date from title (format: "Jun 2, 2025, 2:46 PM GMT+2")
                                    try:
                                        dt = datetime.strptime(title_attr.split(",")[0] + title_attr.split(",")[1], "%b %d %Y")
                                        last_updated = dt.strftime("%Y-%m-%d")
                                        coin["github_last_updated"] = last_updated
                                        print(f"📅 Found last update date for {coin['name']}: {last_updated}")
                                        break
                                    except ValueError as e:
                                        print(f"❌ Error parsing title date for {coin['name']}: {e}")
                                        continue
                                
                                # If neither attribute is available, try the text content
                                text = element.text.strip()
                                if text:
                                    try:
                                        dt = datetime.strptime(text, "%b %d, %Y")
                                        last_updated = dt.strftime("%Y-%m-%d")
                                        coin["github_last_updated"] = last_updated
                                        print(f"📅 Found last update date for {coin['name']}: {last_updated}")
                                        break
                                    except ValueError as e:
                                        print(f"❌ Error parsing text date for {coin['name']}: {e}")
                                        continue
                            except Exception as e:
                                print(f"❌ Error processing update date for {coin['name']}: {e}")
                                continue
                    except Exception as e:
                        print(f"❌ Error finding update date for {coin['name']}: {e}")

                    # Find all star and fork icons before the Repositories section
                    try:
                        # First find the Repositories section if it exists
                        repo_sections = self.driver.find_elements(
                            By.XPATH,
                            "//h2[contains(text(), 'Repositories')]"
                        )
                        
                        if repo_sections:
                            # Get all elements before the Repositories section
                            elements_before_repo = self.driver.find_elements(
                                By.XPATH,
                                f"//*[preceding::h2[contains(text(), 'Repositories')]]"
                            )
                        else:
                            # If no Repositories section, check all elements
                            elements_before_repo = self.driver.find_elements(By.XPATH, "//*")

                        # Find all star and fork icons in these elements
                        total_stars = 0
                        total_forks = 0
                        processed_elements = set()  # Keep track of processed elements to avoid duplicates
                        for element in elements_before_repo:
                            try:
                                # Skip if we've already processed this element
                                if element in processed_elements:
                                    continue
                                
                                # Find star icons
                                star_icons = element.find_elements(
                                    By.CSS_SELECTOR,
                                    'svg[aria-label="stars"]'
                                )
                                
                                # Find fork icons
                                fork_icons = element.find_elements(
                                    By.CSS_SELECTOR,
                                    'svg[aria-label="forks"]'
                                )
                                
                                # Process star icons
                                for icon in star_icons:
                                    try:
                                        if icon in processed_elements:
                                            continue
                                        
                                        parent = icon.find_element(By.XPATH, "./..")
                                        if parent in processed_elements:
                                            continue
                                        
                                        stars_text = parent.text.strip()
                                        print(f"🔍 Raw star text for {coin['name']}: '{stars_text}'")
                                        
                                        if stars_text and any(c.isdigit() for c in stars_text):
                                            match = re.search(r'(\d+(?:\.\d+)?)\s*([KkMmBb]?)\b', stars_text)
                                            if match:
                                                num_text, suffix = match.groups()
                                                print(f"📊 Found number: {num_text} with suffix: {suffix}")
                                                
                                                try:
                                                    star_count = float(num_text)
                                                    if suffix.upper() == 'K':
                                                        star_count *= 1000
                                                    elif suffix.upper() == 'M':
                                                        star_count *= 1000000
                                                    elif suffix.upper() == 'B':
                                                        star_count *= 1000000000
                                                    
                                                    if star_count > 0:
                                                        total_stars += star_count
                                                        print(f"✅ Added {star_count} stars for {coin['name']}")
                                                except ValueError as e:
                                                    print(f"❌ Could not parse star count '{num_text}' for {coin['name']}: {e}")
                                                    continue
                                            else:
                                                print(f"❌ No valid number found in '{stars_text}' for {coin['name']}")
                                        
                                        processed_elements.add(icon)
                                        processed_elements.add(parent)
                                        processed_elements.add(element)
                                    except Exception as e:
                                        print(f"❌ Error processing star icon for {coin['name']}: {e}")
                                        continue

                                # Process fork icons
                                for icon in fork_icons:
                                    try:
                                        if icon in processed_elements:
                                            continue
                                        
                                        parent = icon.find_element(By.XPATH, "./..")
                                        if parent in processed_elements:
                                            continue
                                        
                                        forks_text = parent.text.strip()
                                        print(f"🔍 Raw fork text for {coin['name']}: '{forks_text}'")
                                        
                                        if forks_text and any(c.isdigit() for c in forks_text):
                                            match = re.search(r'(\d+(?:\.\d+)?)\s*([KkMmBb]?)\b', forks_text)
                                            if match:
                                                num_text, suffix = match.groups()
                                                print(f"📊 Found number: {num_text} with suffix: {suffix}")
                                                
                                                try:
                                                    fork_count = float(num_text)
                                                    if suffix.upper() == 'K':
                                                        fork_count *= 1000
                                                    elif suffix.upper() == 'M':
                                                        fork_count *= 1000000
                                                    elif suffix.upper() == 'B':
                                                        fork_count *= 1000000000
                                                    
                                                    if fork_count > 0:
                                                        total_forks += fork_count
                                                        print(f"✅ Added {fork_count} forks for {coin['name']}")
                                                except ValueError as e:
                                                    print(f"❌ Could not parse fork count '{num_text}' for {coin['name']}: {e}")
                                                    continue
                                            else:
                                                print(f"❌ No valid number found in '{forks_text}' for {coin['name']}")
                                        
                                        processed_elements.add(icon)
                                        processed_elements.add(parent)
                                        processed_elements.add(element)
                                    except Exception as e:
                                        print(f"❌ Error processing fork icon for {coin['name']}: {e}")
                                        continue

                            except Exception as e:
                                print(f"❌ Error processing element for {coin['name']}: {e}")
                                continue

                        if total_stars > 0:
                            coin["github_stars"] = total_stars
                            print(f"✅ {coin['name']}: Total {coin['github_stars']} stars")
                        else:
                            print(f"❌ No stars found for {coin['name']}")

                        if total_forks > 0:
                            coin["github_forks"] = total_forks
                            print(f"✅ {coin['name']}: Total {coin['github_forks']} forks")
                        else:
                            print(f"❌ No forks found for {coin['name']}")

                    except Exception as e:
                        print(f"❌ Error finding stars/forks for {coin['name']}: {e}")

                    if not coin.get("github_stars") or not coin.get("github_forks"):
                        print(f"❌ Could not find stars/forks for {coin['name']}")
                        self._save_debug_file(self.driver.page_source, "debug_github", coin['name'])

                    time.sleep(2)  # Rate limiting
                except Exception as e:
                    print(f"❌ Error scraping GitHub for {coin['name']}: {e}")
                finally:
                    try:
                        if coin["_handle"] in self.driver.window_handles:
                    self.driver.close()
                    except Exception as e:
                        print(f"⚠️ Error closing window for {coin['name']}: {e}")
                    
                    # Always switch back to main window if it exists
                    try:
                        if self.main in self.driver.window_handles:
                            self.driver.switch_to.window(self.main)
                    except Exception as e:
                        print(f"⚠️ Error switching to main window: {e}")
                        # If main window is lost, try to get a new handle
                        if self.driver.window_handles:
                            self.main = self.driver.window_handles[0]
                    self.driver.switch_to.window(self.main)

    def save_results(self):
        """Save results in multiple formats"""
        if not self.coins:
            print("⚠️ No data to save")
            return

        # Create filenames with current date
        base_filename = DATA_DIR / f'crypto_data_{self.current_date}'
        
        # Save as JSON
        json_filename = f'{base_filename}.json'
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.coins, f, indent=2)
        print(f"💾 Saved JSON data to {json_filename}")

        # Save as CSV
        csv_filename = f'{base_filename}.csv'
        df = pd.DataFrame(self.coins)
        df.to_csv(csv_filename, index=False)
        print(f"💾 Saved CSV data to {csv_filename}")

        # Save as Parquet
        parquet_filename = f'{base_filename}.parquet'
        df.to_parquet(parquet_filename)
        print(f"💾 Saved Parquet data to {parquet_filename}")

    def close(self):
        """Close the browser"""
        self.driver.quit()

def main():
    scraper = CryptoScraper(headless=True)
    try:
        scraper.collect_coins()
        scraper._extract_social_links()
        scraper._scrape_twitter_followers()
        scraper._scrape_github_stars()
        scraper.save_results()
    finally:
        scraper.close()

if __name__ == "__main__":
    main() 