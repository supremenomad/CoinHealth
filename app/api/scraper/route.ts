import { NextResponse } from "next/server"
import { spawn } from "child_process"
import { join } from "path"

export async function POST() {
  try {
    // Path to your Python script
    const pythonScriptPath = join(process.cwd(), "crypto_twitter_scraper.py")

    return new Promise((resolve) => {
      // Spawn the Python process
      const pythonProcess = spawn("python3", [pythonScriptPath], {
        cwd: process.cwd(),
        stdio: ["pipe", "pipe", "pipe"],
      })

      let output = ""
      let errorOutput = ""

      pythonProcess.stdout.on("data", (data) => {
        output += data.toString()
        console.log("Python output:", data.toString())
      })

      pythonProcess.stderr.on("data", (data) => {
        errorOutput += data.toString()
        console.error("Python error:", data.toString())
      })

      pythonProcess.on("close", (code) => {
        if (code === 0) {
          resolve(
            NextResponse.json({
              success: true,
              message: "Scraper completed successfully",
              output: output,
              timestamp: new Date().toISOString(),
            }),
          )
        } else {
          resolve(
            NextResponse.json(
              {
                success: false,
                message: "Scraper failed",
                error: errorOutput,
                code: code,
                timestamp: new Date().toISOString(),
              },
              { status: 500 },
            ),
          )
        }
      })

      pythonProcess.on("error", (error) => {
        resolve(
          NextResponse.json(
            {
              success: false,
              message: "Failed to start scraper",
              error: error.message,
              timestamp: new Date().toISOString(),
            },
            { status: 500 },
          ),
        )
      })
    })
  } catch (error) {
    console.error("Scraper API Error:", error)
    return NextResponse.json(
      {
        success: false,
        error: "Failed to trigger scraper",
        message: error instanceof Error ? error.message : "Unknown error",
      },
      { status: 500 },
    )
  }
}
