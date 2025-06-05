# 🚀 Coin Health

This is a **real, working** scraper that uses Selenium to extract cryptocurrency data from CoinGecko and Twitter follower counts.

## 🛠️ Setup

### Prerequisites
- Python 3.7+
- Chrome browser installed
- Internet connection

### Installation

1. **Clone/Download the files**
2. **Run setup script:**
   \`\`\`bash
   chmod +x setup.sh
   ./setup.sh
   \`\`\`

3. **Or manual setup:**
   \`\`\`bash
   python3 -m venv crypto_scraper_env
   source crypto_scraper_env/bin/activate
   pip install -r requirements.txt
   \`\`\`

## 🎯 Usage

### Step 1: Scrape CoinGecko
\`\`\`bash
source crypto_scraper_env/bin/activate
python real_coingecko_scraper.py
\`\`\`

**What it does:**
- ✅ Visits CoinGecko.com using real Chrome browser
- ✅ Extracts top 10 cryptocurrencies from the table
- ✅ Visits each coin's individual page
- ✅ Searches for Twitter links using the exact pattern you mentioned
- ✅ Saves results to `crypto_coins_real.json` and `TweeterX_real.txt`

### Step 2: Scrape Twitter Followers
\`\`\`bash
python real_twitter_scraper.py
\`\`\`

**What it does:**
- ✅ Loads crypto data from Step 1
- ✅ Visits each Twitter/X profile using real Chrome browser
- ✅ Extracts follower counts using `[data-testid="UserFollowers"]` selectors
- ✅ Handles rate limiting (10 second delays)
- ✅ Saves results to `crypto_twitter_followers_real.json`

## 📁 Output Files

- `crypto_coins_real.json` - CoinGecko data with Twitter accounts
- `TweeterX_real.txt` - List of Twitter URLs
- `crypto_coins_real.csv` - CoinGecko data in CSV format
- `crypto_twitter_followers_real.json` - Final data with follower counts
- `crypto_twitter_followers_real.csv` - Final data in CSV format

## ⚙️ Configuration

### Headless Mode
\`\`\`python
# In the scripts, change this line:
scraper = CoinGeckoScraper(headless=True)  # True = no browser window
\`\`\`

### Number of Coins
\`\`\`python
# In real_coingecko_scraper.py:
coins = scraper.scrape_top_coins(limit=50)  # Change from 10 to 50
\`\`\`

### Rate Limiting
\`\`\`python
# In real_twitter_scraper.py:
time.sleep(10)  # Increase delay between Twitter requests
\`\`\`

## 🔧 Troubleshooting

### Chrome Driver Issues
\`\`\`bash
pip install webdriver-manager
\`\`\`

### Twitter Rate Limiting
- Increase delays between requests
- Use residential proxies
- Implement retry logic

### CoinGecko Blocking
- Add random delays
- Rotate user agents
- Use proxy rotation

## 🚨 Important Notes

### Legal & Ethical
- ✅ Respects robots.txt
- ✅ Implements rate limiting
- ✅ For educational/research purposes
- ⚠️ Check website terms of service
- ⚠️ Don't overload servers

### Twitter/X Limitations
- May require login for some profiles
- Rate limiting is strict
- Some profiles may be private
- Follower counts may be approximate

## 📊 Expected Output

\`\`\`
🚀 Starting CoinGecko scraping for top 10 crypto coins...
📊 Visiting CoinGecko.com...
✅ Page loaded, finding cryptocurrency table...
🔍 Processing 1: Bitcoin (BTC) - https://www.coingecko.com/en/coins/bitcoin
✅ Bitcoin: Found Twitter @bitcoin
🔍 Processing 2: Ethereum (ETH) - https://www.coingecko.com/en/coins/ethereum
✅ Ethereum: Found Twitter @ethereum
...
📈 SCRAPING SUMMARY:
Total coins processed: 10
Coins with Twitter: 8
Success rate: 80.0%
\`\`\`

## 🎯 Integration with Next.js

To use this data in your Next.js app, copy the JSON files to your project and update the API routes to read from these real files instead of the simulated data.

## 🔄 Automation

Set up cron jobs to run the scrapers automatically:
\`\`\`bash
# Run every 6 hours
0 */6 * * * /path/to/crypto_scraper_env/bin/python /path/to/real_coingecko_scraper.py
30 */6 * * * /path/to/crypto_scraper_env/bin/python /path/to/real_twitter_scraper.py
