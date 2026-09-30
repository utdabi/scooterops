import { Compass, Radar } from "lucide-react"

interface AppHeaderProps {
  freshnessTimestamp?: string
  isRefreshing: boolean
  onTakeTour: () => void
}

function formatFreshness(timestamp?: string) {
  if (!timestamp) return "Awaiting plan"
  return new Intl.DateTimeFormat("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    timeZone: "America/Chicago",
    timeZoneName: "short",
  }).format(new Date(timestamp))
}

export function AppHeader({ freshnessTimestamp, isRefreshing, onTakeTour }: AppHeaderProps) {
  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-white/10 bg-[#0b0d10] px-4">
      <div className="flex items-center gap-2.5">
        <div className="flex size-6 items-center justify-center rounded-md bg-cyan-500/15">
          <Radar className="size-3.5 text-cyan-400" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-zinc-100">ScooterOps</span>
        <span className="text-xs text-zinc-500">Fleet Operations Command Center</span>
      </div>

      <div className="flex items-center gap-4 text-xs text-zinc-500">
        <span>Chicago Metro</span>
        <button
          type="button"
          onClick={onTakeTour}
          className="flex items-center gap-1.5 rounded-sm border border-cyan-400/45 bg-cyan-500/[0.07] px-2 py-1 font-medium text-cyan-300 transition-all hover:border-cyan-300/70 hover:bg-cyan-500/[0.12] hover:text-cyan-200 hover:shadow-[0_0_12px_rgba(34,211,238,0.16)] focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-cyan-400/70"
        >
          <Compass className="size-3" />
          Take Tour
        </button>
        <span className="flex items-center gap-1.5">
          <span className={`size-1.5 rounded-full ${isRefreshing ? "bg-cyan-400" : "bg-emerald-400"}`} />
          {isRefreshing ? "Refreshing" : "Current"}
        </span>
        <span className="font-mono tabular-nums">{formatFreshness(freshnessTimestamp)}</span>
      </div>
    </header>
  )
}
