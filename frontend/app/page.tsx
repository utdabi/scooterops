"use client"

import { useCallback, useEffect, useState } from "react"
import { AgentTracePanel } from "@/components/agent-trace-panel"
import { AppHeader } from "@/components/app-header"
import { MapPanel } from "@/components/map-panel"
import { RebalanceStrip } from "@/components/rebalance-strip"
import { refreshAnalysis, type AnalysisResult } from "@/lib/fleet-data"
import { useScooterOpsTour } from "@/lib/use-scooterops-tour"

export default function Page() {
  const [mode, setMode] = useState<"before" | "proposed">("proposed")
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null)
  const [isRefreshing, setIsRefreshing] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const refreshPlan = useCallback(async () => {
    try {
      setIsRefreshing(true)
      setError(null)
      const nextAnalysis = await refreshAnalysis()
      setAnalysis(nextAnalysis)
    } catch (requestError) {
      console.error("Failed to refresh ScooterOps analysis", requestError)
      setError(requestError instanceof Error ? requestError.message : "Analysis request failed")
    } finally {
      setIsRefreshing(false)
    }
  }, [])

  useEffect(() => {
    void refreshPlan()
  }, [refreshPlan])

  const showProposedRoutes = useCallback(() => setMode("proposed"), [])
  const startTour = useScooterOpsTour({
    isDashboardReady: !isRefreshing && analysis !== null,
    showProposedRoutes,
  })

  return (
    <div className="dark flex h-screen w-full flex-col overflow-hidden bg-[#08090b] text-zinc-100">
      <AppHeader freshnessTimestamp={analysis?.freshness_timestamp} isRefreshing={isRefreshing} onTakeTour={startTour} />

      <div className="flex min-h-0 flex-1">
        <div className="min-w-0 flex-[7]">
          <MapPanel mode={mode} onModeChange={setMode} analysis={analysis} error={error} />
        </div>
        <div className="w-[320px] shrink-0">
          <AgentTracePanel analysis={analysis} isRefreshing={isRefreshing} error={error} />
        </div>
      </div>

      <div className="h-16 shrink-0">
        <RebalanceStrip analysis={analysis} isRefreshing={isRefreshing} onRefresh={refreshPlan} />
      </div>
    </div>
  )
}
