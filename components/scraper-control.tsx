"use client"

import { useState } from "react"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Play, Square, RefreshCw, AlertCircle, CheckCircle } from "lucide-react"

export function ScraperControl() {
  const [isRunning, setIsRunning] = useState(false)
  const [lastRun, setLastRun] = useState<Date | null>(null)
  const [status, setStatus] = useState<"idle" | "running" | "success" | "error">("idle")
  const [output, setOutput] = useState<string>("")

  const runScraper = async () => {
    setIsRunning(true)
    setStatus("running")
    setOutput("Starting scraper...\n")

    try {
      const response = await fetch("/api/scraper", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      })

      const result = await response.json()

      if (result.success) {
        setStatus("success")
        setOutput(result.output || "Scraper completed successfully")
        setLastRun(new Date())
      } else {
        setStatus("error")
        setOutput(result.error || "Scraper failed")
      }
    } catch (error) {
      setStatus("error")
      setOutput(`Error: ${error instanceof Error ? error.message : "Unknown error"}`)
    } finally {
      setIsRunning(false)
    }
  }

  const getStatusIcon = () => {
    switch (status) {
      case "running":
        return <RefreshCw className="h-4 w-4 animate-spin" />
      case "success":
        return <CheckCircle className="h-4 w-4 text-green-500" />
      case "error":
        return <AlertCircle className="h-4 w-4 text-red-500" />
      default:
        return <Square className="h-4 w-4" />
    }
  }

  const getStatusBadge = () => {
    switch (status) {
      case "running":
        return <Badge variant="secondary">Running</Badge>
      case "success":
        return <Badge className="bg-green-100 text-green-800">Success</Badge>
      case "error":
        return <Badge variant="destructive">Error</Badge>
      default:
        return <Badge variant="outline">Idle</Badge>
    }
  }

  return (
    <Card className="mb-6">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            {getStatusIcon()}
            Scraper Control
          </CardTitle>
          {getStatusBadge()}
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-4 mb-4">
          <Button onClick={runScraper} disabled={isRunning} className="flex items-center gap-2">
            <Play className="h-4 w-4" />
            {isRunning ? "Running..." : "Run Scraper"}
          </Button>

          {lastRun && <div className="text-sm text-slate-600">Last run: {lastRun.toLocaleString()}</div>}
        </div>

        {output && (
          <div className="bg-slate-100 rounded-md p-3 max-h-40 overflow-y-auto">
            <pre className="text-sm whitespace-pre-wrap">{output}</pre>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
