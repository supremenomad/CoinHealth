#!/bin/bash

echo "🚀 Setting up Real Crypto Twitter Scraper"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv crypto_scraper_env

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source crypto_scraper_env/bin/activate

# Install requirements
echo "📥 Installing Python packages..."
pip install -r requirements.txt

# Install Chrome WebDriver
echo "🌐 Installing Chrome WebDriver..."
pip install webdriver-manager

echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "1. Activate environment: source crypto_scraper_env/bin/activate"
echo "2. Run CoinGecko scraper: python real_coingecko_scraper.py"
echo "3. Run Twitter scraper: python real_twitter_scraper.py"
echo ""
echo "📋 Requirements:"
echo "- Chrome browser installed"
echo "- Internet connection"
echo "- Python 3.7+"
