import { ArrowLeft, ArrowRight, CheckCircle2, CircleDashed, Loader2, ShieldCheck, XCircle } from "lucide-react"
import { useState } from "react"
import { type AnalysisResult, type TraceStep } from "@/lib/fleet-data"
import { Separator } from "@/components/ui/separator"
import { cn } from "@/lib/utils"

function StepIcon({ status }: { status: TraceStep["status"] }) {
  if (status === "complete") return <CheckCircle2 className="size-4 text-emerald-400" />
  return <XCircle className="size-4 text-red-400" />
}

interface AgentTracePanelProps {
  analysis: AnalysisResult | null
  isRefreshing: boolean
  error: string | null
}

function formatTraceTime(timestamp: string) {
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "America/Chicago",
  }).format(new Date(timestamp))
}

export function AgentTracePanel({ analysis, isRefreshing, error }: AgentTracePanelProps) {
  const [view, setView] = useState<"agent" | "movements">("agent")
  const traceSteps = analysis?.agent.trace ?? []
  const approved = analysis?.validation.status === "APPROVED"

  if (view === "movements") {
    return (
      <div data-tour="agent-trace" className="flex h-full flex-col border-l border-white/10 bg-[#0b0d10]">
        <div className="border-b border-white/10 px-4 py-3">
          <button
            type="button"
            onClick={() => setView("agent")}
            className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-zinc-300 transition-colors hover:text-cyan-300"
          >
            <ArrowLeft className="size-4" />
            Proposed movements
          </button>
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-4">
          {analysis?.moves.length ? <div className="space-y-2">
            {analysis.moves.map((move) => (
              <div key={move.id} className="flex items-center gap-2 rounded-md border border-white/10 bg-white/[0.02] px-3 py-2.5">
                <span className="min-w-0 flex-1 truncate text-xs font-medium text-zinc-200">{move.source}</span>
                <ArrowRight className="size-3 shrink-0 text-cyan-400" />
                <span className="min-w-0 flex-1 truncate text-right text-xs font-medium text-zinc-200">{move.destination}</span>
                <span className="ml-1 shrink-0 rounded-full bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[10px] text-cyan-300">{move.scooters}</span>
              </div>
            ))}
          </div> : <p className="text-xs text-zinc-500">No proposed movements are available.</p>}
        </div>

        <div className="border-t border-white/10 px-4 py-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500">Plan summary</p>
          <p className="mt-1 text-xs tabular-nums text-zinc-300">
            {analysis ? `${analysis.summary.total_scooters_moved} scooters across ${analysis.moves.length} movements` : "No plan available"}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div data-tour="agent-trace" className="flex h-full flex-col border-l border-white/10 bg-[#0b0d10]">
      <div className="border-b border-white/10 px-4 py-3">
        <div className="flex items-center justify-between">
          <h2 className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Autonomous Rebalance Agent</h2>
            <span className={`flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[10px] font-medium ${isRefreshing ? "border-cyan-500/30 bg-cyan-500/10 text-cyan-400" : "border-emerald-500/30 bg-emerald-500/10 text-emerald-400"}`}>
            {isRefreshing ? <Loader2 className="size-3 animate-spin" /> : <span className="size-1.5 rounded-full bg-emerald-400" />}
            {isRefreshing ? "RUNNING" : "COMPLETE"}
            </span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-4 py-4">
        {traceSteps.length > 0 ? <ol className="relative space-y-0">
          {traceSteps.map((step, i) => (
            <li key={step.id} className="relative flex gap-3 pb-6 last:pb-0">
              {i < traceSteps.length - 1 && (
                <span className="absolute left-[7px] top-5 h-full w-px bg-white/10" aria-hidden="true" />
              )}
              <div className="mt-0.5 shrink-0">
                <StepIcon status={step.status} />
              </div>
              <div className="min-w-0">
                <div className="flex items-baseline justify-between gap-2">
                  <p className="text-sm font-medium text-zinc-100">{step.label}</p>
                  <span className="shrink-0 text-[10px] tabular-nums text-zinc-500">{formatTraceTime(step.timestamp)}</span>
                </div>
                <p className="mt-0.5 text-xs leading-snug text-zinc-500">{step.detail}</p>
              </div>
            </li>
          ))}
        </ol> : <div className="flex items-center gap-2 py-2 text-xs text-zinc-500">
          {isRefreshing ? <><CircleDashed className="size-4 animate-spin text-cyan-400" /> Running the real analysis workflow</> : "No completed workflow is available."}
        </div>}

        <Separator className="my-4 bg-white/10" />

        <div className={cn(
          "flex items-center gap-3 rounded-md border px-3 py-3",
          approved ? "border-emerald-500/30 bg-emerald-500/[0.06]" : "border-white/10 bg-white/[0.02]",
        )}>
          <ShieldCheck className={`size-5 shrink-0 ${approved ? "text-emerald-400" : "text-zinc-500"}`} />
          <div>
            {approved ? <button
              type="button"
              onClick={() => setView("movements")}
              className="flex items-center gap-1.5 text-sm font-semibold text-emerald-300 transition-colors hover:text-cyan-300"
            >
              View movements
              <ArrowRight className="size-3.5" />
            </button> : <p className="text-sm font-semibold text-zinc-400">{analysis?.validation.status ?? "PENDING"}</p>}
            <p className="text-xs text-zinc-500">{error ?? (analysis ? "Move budget, fleet conservation, source inventory, and imbalance improvement validated." : "Validation result will appear after the workflow completes")}</p>
          </div>
        </div>
      </div>

      <div className="border-t border-white/10 px-4 py-3">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-zinc-500">Gap legend</p>
          <p className="mt-1 text-xs text-zinc-400">Gap = demand share − supply share</p>
          <p className="mt-0.5 text-[10px] text-zinc-500">+ under-supplied · − over-supplied</p>
        </div>
        <div className="mt-3 border-t border-white/10 pt-3">
          <p className="text-[10px] uppercase tracking-wider text-zinc-500">Solver</p>
          <p className="mt-1 font-mono text-xs text-zinc-400">scipy.optimize.milp</p>
        </div>
      </div>
    </div>
  )
}
