"use client"

import { FleetMap } from "@/components/fleet-map"
import { type AnalysisResult } from "@/lib/fleet-data"
import { cn } from "@/lib/utils"

interface MapPanelProps {
  mode: "before" | "proposed"
  onModeChange: (mode: "before" | "proposed") => void
  analysis: AnalysisResult | null
  error: string | null
}

export function MapPanel({ mode, onModeChange, analysis, error }: MapPanelProps) {
  return (
    <div className="flex h-full flex-col gap-3 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-sm font-semibold text-zinc-100">Chicago Fleet Map</h1>
          <p className="text-xs text-zinc-500">{analysis ? `${analysis.fleet.current_lime_scooter_supply} current Lime scooters across ${analysis.fleet.analyzed_community_areas} analyzed community areas` : "Live supply and seasonal demand share will appear after analysis"}</p>
        </div>
          <div className="flex items-center gap-4">
          <div data-tour="supply-demand-gap" className="flex items-center gap-3 text-[10px] text-zinc-500"><span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-red-500" /> Under-supplied</span><span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-amber-500" /> Supply-demand gap</span><span className="flex items-center gap-1.5"><span className="size-2 rounded-full bg-sky-500" /> Over-supplied</span></div>
          <div className="flex items-center rounded-md border border-white/10 bg-white/[0.03] p-0.5 text-xs">
            <button type="button" onClick={() => onModeChange("before")} className={cn("rounded-[5px] px-2.5 py-1 font-medium transition-colors", mode === "before" ? "bg-white/10 text-zinc-100" : "text-zinc-500 hover:text-zinc-300")}>Before</button>
            <button type="button" onClick={() => onModeChange("proposed")} className={cn("rounded-[5px] px-2.5 py-1 font-medium transition-colors", mode === "proposed" ? "bg-cyan-500/20 text-cyan-300" : "text-zinc-500 hover:bg-white/5 hover:text-zinc-300")}>Proposed</button>
          </div>
        </div>
      </div>
      <div data-tour="fleet-map" className="relative min-h-0 flex-1 overflow-x-auto">
        {analysis ? <FleetMap mode={mode} zones={analysis.zones} moves={analysis.moves} /> : <div className="flex h-full items-center justify-center rounded-lg border border-white/10 bg-[#0a0c0f] text-sm text-zinc-500">{error ?? "Running live analysis…"}</div>}
      </div>
    </div>
  )
}
