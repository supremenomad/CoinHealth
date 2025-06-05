"use client"

import { useState, useEffect } from "react"
import { Search, TrendingUp, Users, ExternalLink, RefreshCw, Play, AlertCircle, CheckCircle } from "lucide-react"
import { Input } from "@/components/ui/input"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface CryptoData {
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

export default function CryptoDashboard() {
  const [cryptoData, setCryptoData] = useState<CryptoData[]>([])
  const [loading, setLoading] = useState(true)
  const [scraping, setScraping] = useState(false)
  const [searchTerm, setSearchTerm] = useState("")
  const [sortBy, setSortBy] = useState<"rank" | "followers" | "market_cap">("rank")
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)
  const [scrapingStatus, setScrapingStatus] = useState<string>("")
  const [scrapingStep, setScrapingStep] = useState<"idle" | "coingecko" | "twitter" | "complete">("idle")

  const fetchData = async () => {
    setLoading(true)
    try {
      const response = await fetch("/api/followers")
      if (response.ok) {
        const data = await response.json()
        setCryptoData(data)
        setLastRefresh(new Date())
      } else {
        console.error("Failed to fetch data:", response.statusText)
      }
    } catch (error) {
      console.error("Error fetching data:", error)
    } finally {
      setLoading(false)
    }
  }

  const runFullScraper = async () => {
    setScraping(true)
    setScrapingStep("coingecko")
    setScrapingStatus("🚀 Starting CoinGecko scraper...")

    try {
      // First run the CoinGecko scraper
      const coinGeckoResponse = await fetch("/api/scrape-coingecko", {
        method: "POST",
      })

      if (coinGeckoResponse.ok) {
        const coinGeckoResult = await coinGeckoResponse.json()
        setScrapingStatus(
          `✅ CoinGecko: Found ${coinGeckoResult.twitterAccounts} Twitter accounts from ${coinGeckoResult.totalCoins} coins`,
        )
        setScrapingStep("twitter")

        // Wait a moment then run Twitter scraper with the CoinGecko data
        setTimeout(async () => {
          setScrapingStatus("🐦 Starting Twitter follower scraper...")

          const twitterResponse = await fetch("/api/scrape-twitter", {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify({
              cryptoData: coinGeckoResult.coinData,
              twitterUrls: coinGeckoResult.twitterUrls,
            }),
          })

          if (twitterResponse.ok) {
            const twitterResult = await twitterResponse.json()
            setScrapingStatus(`✅ Twitter: Successfully scraped ${twitterResult.scraped} accounts`)
            setScrapingStep("complete")

            // Store the scraped data
            await fetch("/api/followers", {
              method: "POST",
              headers: {
                "Content-Type": "application/json",
              },
              body: JSON.stringify({
                data: twitterResult.data,
              }),
            })

            // Refresh the data
            await fetchData()
            setScrapingStatus("🎉 Scraping complete! Data updated.")
          } else {
            setScrapingStatus("❌ Twitter scraping failed")
            setScrapingStep("idle")
          }
        }, 3000)
      } else {
        setScrapingStatus("❌ CoinGecko scraping failed")
        setScrapingStep("idle")
      }
    } catch (error) {
      setScrapingStatus(`❌ Error: ${error}`)
      setScrapingStep("idle")
    } finally {
      setTimeout(() => {
        setScraping(false)
        setScrapingStep("idle")
      }, 5000)
    }
  }

  useEffect(() => {
    fetchData()
  }, [])

  const formatFollowers = (followers: string) => {
    if (!followers || followers === "0") return "No data"
    return followers
  }

  const formatMarketCap = (marketCap: number) => {
    if (!marketCap) return "N/A"
    if (marketCap >= 1e9) return `$${(marketCap / 1e9).toFixed(2)}B`
    if (marketCap >= 1e6) return `$${(marketCap / 1e6).toFixed(2)}M`
    if (marketCap >= 1e3) return `$${(marketCap / 1e3).toFixed(2)}K`
    return `$${marketCap.toFixed(2)}`
  }

  const formatPrice = (price: number) => {
    if (!price) return "N/A"
    if (price >= 1) return `$${price.toLocaleString()}`
    return `$${price.toFixed(6)}`
  }

  const parseFollowers = (followers: string): number => {
    if (!followers || followers === "0") return 0
    const num = Number.parseFloat(followers.replace(/[,]/g, ""))
    if (followers.includes("M") || followers.includes("m")) return num * 1000000
    if (followers.includes("K") || followers.includes("k")) return num * 1000
    return num
  }

  const filteredAndSortedData = cryptoData
    .filter(
      (coin) =>
        coin.coin_name?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        coin.symbol?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        coin.twitter_handle?.toLowerCase().includes(searchTerm.toLowerCase()),
    )
    .sort((a, b) => {
      switch (sortBy) {
        case "followers":
          return parseFollowers(b.followers) - parseFollowers(a.followers)
        case "market_cap":
          return (b.market_cap || 0) - (a.market_cap || 0)
        case "rank":
        default:
          return (a.rank || 999) - (b.rank || 999)
      }
    })

  const totalCoins = cryptoData.length
  const coinsWithTwitter = cryptoData.filter((coin) => coin.twitter_handle).length
  const coinsWithFollowers = cryptoData.filter(
    (coin) => coin.followers && coin.followers !== "0" && coin.followers !== "No Twitter",
  ).length

  const getScrapingIcon = () => {
    switch (scrapingStep) {
      case "coingecko":
        return <RefreshCw className="h-4 w-4 animate-spin" />
      case "twitter":
        return <RefreshCw className="h-4 w-4 animate-spin" />
      case "complete":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      default:
        return <AlertCircle className="h-4 w-4" />
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 p-4">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-slate-900 mb-2">Crypto Twitter Analytics</h1>
          <p className="text-slate-600">Real-time follower counts for top cryptocurrency projects</p>
        </div>

        {/* Scraper Control */}
        {(scraping || scrapingStatus) && (
          <Alert className="mb-6">
            {getScrapingIcon()}
            <AlertDescription>{scrapingStatus}</AlertDescription>
          </Alert>
        )}

        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-4 w-4" />
              Live Data Scraper
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-4">
              <Button onClick={runFullScraper} disabled={scraping} className="flex items-center gap-2">
                <RefreshCw className={`h-4 w-4 ${scraping ? "animate-spin" : ""}`} />
                {scraping ? "Scraping..." : "Get Real Data"}
              </Button>
              <p className="text-sm text-slate-600">
                This will scrape live data from CoinGecko and Twitter (simulated for demo)
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Coins</CardTitle>
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{totalCoins}</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">With Twitter</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{coinsWithTwitter}</div>
              <p className="text-xs text-muted-foreground">
                {totalCoins > 0 ? Math.round((coinsWithTwitter / totalCoins) * 100) : 0}% coverage
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Follower Data</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{coinsWithFollowers}</div>
              <p className="text-xs text-muted-foreground">
                {coinsWithTwitter > 0 ? Math.round((coinsWithFollowers / coinsWithTwitter) * 100) : 0}% scraped
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Last Updated</CardTitle>
              <RefreshCw className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-sm font-bold">{lastRefresh ? lastRefresh.toLocaleTimeString() : "Never"}</div>
              <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} className="mt-2">
                <RefreshCw className={`h-3 w-3 mr-1 ${loading ? "animate-spin" : ""}`} />
                Refresh
              </Button>
            </CardContent>
          </Card>
        </div>

        {/* Controls */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-slate-400 h-4 w-4" />
            <Input
              placeholder="Search coins, symbols, or Twitter handles..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>

          <div className="flex gap-2">
            <Button variant={sortBy === "rank" ? "default" : "outline"} onClick={() => setSortBy("rank")} size="sm">
              Rank
            </Button>
            <Button
              variant={sortBy === "followers" ? "default" : "outline"}
              onClick={() => setSortBy("followers")}
              size="sm"
            >
              Followers
            </Button>
            <Button
              variant={sortBy === "market_cap" ? "default" : "outline"}
              onClick={() => setSortBy("market_cap")}
              size="sm"
            >
              Market Cap
            </Button>
          </div>
        </div>

        {/* Data Grid */}
        {loading ? (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Array.from({ length: 12 }).map((_, i) => (
              <Card key={i}>
                <CardHeader>
                  <Skeleton className="h-6 w-3/4" />
                  <Skeleton className="h-4 w-1/2" />
                </CardHeader>
                <CardContent>
                  <Skeleton className="h-4 w-full mb-2" />
                  <Skeleton className="h-4 w-2/3" />
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredAndSortedData.map((coin) => (
              <Card key={coin.twitter_url || coin.coin_name} className="hover:shadow-lg transition-shadow">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div>
                      <CardTitle className="text-lg">{coin.coin_name}</CardTitle>
                      <div className="flex items-center gap-2 mt-1">
                        <Badge variant="secondary">{coin.symbol}</Badge>
                        <Badge variant="outline">#{coin.rank}</Badge>
                      </div>
                    </div>
                  </div>
                </CardHeader>

                <CardContent>
                  <div className="space-y-3">
                    {/* Twitter Info */}
                    {coin.twitter_handle ? (
                      <div className="flex items-center justify-between">
                        <div>
                          <p className="text-sm text-slate-600">Twitter Followers</p>
                          <p className="text-xl font-bold text-blue-600">{formatFollowers(coin.followers)}</p>
                        </div>
                        <a
                          href={coin.twitter_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-blue-500 hover:text-blue-700"
                        >
                          <ExternalLink className="h-4 w-4" />
                        </a>
                      </div>
                    ) : (
                      <div>
                        <p className="text-sm text-slate-600">Twitter</p>
                        <p className="text-sm text-slate-400">No account found</p>
                      </div>
                    )}

                    {/* Market Data */}
                    <div className="grid grid-cols-2 gap-4 pt-3 border-t">
                      <div>
                        <p className="text-xs text-slate-600">Price</p>
                        <p className="font-semibold">{formatPrice(coin.price)}</p>
                      </div>
                      <div>
                        <p className="text-xs text-slate-600">Market Cap</p>
                        <p className="font-semibold">{formatMarketCap(coin.market_cap)}</p>
                      </div>
                    </div>

                    {/* Last Updated */}
                    {coin.last_updated && (
                      <div className="pt-2 border-t">
                        <p className="text-xs text-slate-500">
                          Updated: {new Date(coin.last_updated).toLocaleString()}
                        </p>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}

        {!loading && filteredAndSortedData.length === 0 && (
          <div className="text-center py-12">
            <p className="text-slate-500 text-lg">No coins found matching your search.</p>
          </div>
        )}
      </div>
    </div>
  )
}
