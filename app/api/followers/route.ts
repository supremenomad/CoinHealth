import { NextResponse } from "next/server"

interface CryptoFollower {
  coin_name: string
  symbol: string
  twitter_handle: string
  twitter_url: string
  followers: string
  market_cap: number
  price: number
  rank: number
  last_updated: string
}

// Sample data that loads immediately
const sampleData: CryptoFollower[] = [
  {
    coin_name: "Bitcoin",
    symbol: "BTC",
    twitter_handle: "bitcoin",
    twitter_url: "https://x.com/bitcoin",
    followers: "5.2M",
    market_cap: 1280000000000,
    price: 65432.21,
    rank: 1,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "Ethereum",
    symbol: "ETH",
    twitter_handle: "ethereum",
    twitter_url: "https://x.com/ethereum",
    followers: "3.1M",
    market_cap: 425000000000,
    price: 3542.18,
    rank: 2,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "Tether USDt",
    symbol: "USDT",
    twitter_handle: "Tether_to",
    twitter_url: "https://x.com/Tether_to",
    followers: "1.8M",
    market_cap: 125000000000,
    price: 1.0,
    rank: 3,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "BNB",
    symbol: "BNB",
    twitter_handle: "BNBCHAIN",
    twitter_url: "https://x.com/BNBCHAIN",
    followers: "2.4M",
    market_cap: 98000000000,
    price: 672.45,
    rank: 4,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "Solana",
    symbol: "SOL",
    twitter_handle: "solana",
    twitter_url: "https://x.com/solana",
    followers: "1.9M",
    market_cap: 89000000000,
    price: 195.67,
    rank: 5,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "XRP",
    symbol: "XRP",
    twitter_handle: "Ripple",
    twitter_url: "https://x.com/Ripple",
    followers: "3.5M",
    market_cap: 78000000000,
    price: 1.38,
    rank: 6,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "Dogecoin",
    symbol: "DOGE",
    twitter_handle: "dogecoin",
    twitter_url: "https://x.com/dogecoin",
    followers: "2.8M",
    market_cap: 58000000000,
    price: 0.39,
    rank: 7,
    last_updated: new Date().toISOString(),
  },
  {
    coin_name: "Cardano",
    symbol: "ADA",
    twitter_handle: "Cardano",
    twitter_url: "https://x.com/Cardano",
    followers: "1.2M",
    market_cap: 47000000000,
    price: 1.32,
    rank: 8,
    last_updated: new Date().toISOString(),
  },
]

// Store scraped data in memory
let scrapedCryptoData: CryptoFollower[] = []

export async function GET() {
  // Return scraped data if available, otherwise return sample data
  if (scrapedCryptoData.length > 0) {
    console.log(`✅ Returning ${scrapedCryptoData.length} live scraped records`)
    return NextResponse.json(scrapedCryptoData)
  }

  console.log("📊 Returning sample data for preview")
  return NextResponse.json(sampleData)
}

export async function POST(request: Request) {
  try {
    const body = await request.json()

    // Store the scraped data
    if (body.data && Array.isArray(body.data)) {
      scrapedCryptoData = body.data
      console.log(`💾 Stored ${scrapedCryptoData.length} scraped records`)
    }

    return NextResponse.json({
      success: true,
      message: "Data stored successfully",
      count: scrapedCryptoData.length,
    })
  } catch (error) {
    console.error("Error storing data:", error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
