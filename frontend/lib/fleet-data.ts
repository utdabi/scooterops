export interface Zone {
  id: string
  community: string
  available_scooters: number
  predicted_demand_share_pct: number
  supply_share_pct: number
  share_gap_pct_points: number
  x: number
  y: number
}

export interface RebalanceMove {
  id: string
  source: string
  destination: string
  scooters: number
  centroid_distance_km: number
}

export interface TraceStep {
  id: string
  label: string
  detail: string
  status: "complete" | "failed"
  timestamp: string
}

export interface AnalysisResult {
  freshness_timestamp: string
  fleet: {
    current_lime_scooter_supply: number
    analyzed_community_areas: number
    forecast_method: string
  }
  zones: Zone[]
  moves: RebalanceMove[]
  summary: {
    total_scooters_moved: number
    total_centroid_scooter_km: number
    mean_absolute_share_gap_before_pp: number
    mean_absolute_share_gap_after_pp: number
    spatial_imbalance_improvement_pct: number
  }
  validation: {
    status: "APPROVED" | "REJECTED"
    constraints_passed: boolean
    total_scooters_moved: number
    move_budget: number
    mean_absolute_share_gap_before_pp: number
    mean_absolute_share_gap_after_pp: number
    spatial_imbalance_improvement_pct: number
    errors: string[]
  }
  agent: {
    trace: TraceStep[]
    recommendation: string
  }
}

type JsonRecord = Record<string, unknown>

function asRecord(value: unknown, path: string): JsonRecord {
  if (typeof value !== "object" || value === null || Array.isArray(value)) {
    throw new Error(`Analysis response field ${path} must be an object`)
  }

  return value as JsonRecord
}

function asArray(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) {
    throw new Error(`Analysis response field ${path} must be an array`)
  }

  return value
}

function asString(value: unknown, path: string): string {
  if (typeof value !== "string") {
    throw new Error(`Analysis response field ${path} must be a string`)
  }

  return value
}

function asNumber(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw new Error(`Analysis response field ${path} must be a finite number`)
  }

  return value
}

function asBoolean(value: unknown, path: string): boolean {
  if (typeof value !== "boolean") {
    throw new Error(`Analysis response field ${path} must be a boolean`)
  }

  return value
}

function normalizeTimestamp(value: unknown, path: string): string {
  const timestamp = asString(value, path)
  if (Number.isNaN(Date.parse(timestamp))) {
    throw new Error(`Analysis response field ${path} must be an ISO timestamp`)
  }

  return timestamp
}

function normalizeZone(value: unknown, index: number): Zone {
  const path = `zones[${index}]`
  const zone = asRecord(value, path)

  return {
    id: asString(zone.id, `${path}.id`),
    community: asString(zone.community, `${path}.community`),
    available_scooters: asNumber(zone.available_scooters, `${path}.available_scooters`),
    predicted_demand_share_pct: asNumber(zone.predicted_demand_share_pct, `${path}.predicted_demand_share_pct`),
    supply_share_pct: asNumber(zone.supply_share_pct, `${path}.supply_share_pct`),
    share_gap_pct_points: asNumber(zone.share_gap_pct_points, `${path}.share_gap_pct_points`),
    x: asNumber(zone.x, `${path}.x`),
    y: asNumber(zone.y, `${path}.y`),
  }
}

function normalizeMove(value: unknown, index: number): RebalanceMove {
  const path = `moves[${index}]`
  const move = asRecord(value, path)

  return {
    id: asString(move.id, `${path}.id`),
    source: asString(move.source, `${path}.source`),
    destination: asString(move.destination, `${path}.destination`),
    scooters: asNumber(move.scooters, `${path}.scooters`),
    centroid_distance_km: asNumber(move.centroid_distance_km, `${path}.centroid_distance_km`),
  }
}

function normalizeTraceStep(value: unknown, index: number): TraceStep {
  const path = `agent.trace[${index}]`
  const step = asRecord(value, path)
  const status = asString(step.status, `${path}.status`)
  if (status !== "complete" && status !== "failed") {
    throw new Error(`Analysis response field ${path}.status must be complete or failed`)
  }

  return {
    id: asString(step.id, `${path}.id`),
    label: asString(step.label, `${path}.label`),
    detail: asString(step.detail, `${path}.detail`),
    status,
    timestamp: normalizeTimestamp(step.timestamp, `${path}.timestamp`),
  }
}

export function normalizeAnalysisResponse(payload: unknown): AnalysisResult {
  const response = asRecord(payload, "response")
  const fleet = asRecord(response.fleet, "fleet")
  const summary = asRecord(response.summary, "summary")
  const validation = asRecord(response.validation, "validation")
  const agent = asRecord(response.agent, "agent")
  const zones = asArray(response.zones, "zones").map(normalizeZone)
  const moves = asArray(response.moves, "moves").map(normalizeMove)
  const trace = asArray(agent.trace, "agent.trace").map(normalizeTraceStep)
  const validationStatus = asString(validation.status, "validation.status")

  if (validationStatus !== "APPROVED" && validationStatus !== "REJECTED") {
    throw new Error("Analysis response field validation.status must be APPROVED or REJECTED")
  }

  const knownCommunities = new Set(zones.map((zone) => zone.community))
  for (const move of moves) {
    if (!knownCommunities.has(move.source) || !knownCommunities.has(move.destination)) {
      throw new Error(`Analysis response route ${move.id} references a zone that is not on the map`)
    }
  }

  return {
    freshness_timestamp: normalizeTimestamp(response.freshness_timestamp, "freshness_timestamp"),
    fleet: {
      current_lime_scooter_supply: asNumber(fleet.current_lime_scooter_supply, "fleet.current_lime_scooter_supply"),
      analyzed_community_areas: asNumber(fleet.analyzed_community_areas, "fleet.analyzed_community_areas"),
      forecast_method: asString(fleet.forecast_method, "fleet.forecast_method"),
    },
    zones,
    moves,
    summary: {
      total_scooters_moved: asNumber(summary.total_scooters_moved, "summary.total_scooters_moved"),
      total_centroid_scooter_km: asNumber(summary.total_centroid_scooter_km, "summary.total_centroid_scooter_km"),
      mean_absolute_share_gap_before_pp: asNumber(summary.mean_absolute_share_gap_before_pp, "summary.mean_absolute_share_gap_before_pp"),
      mean_absolute_share_gap_after_pp: asNumber(summary.mean_absolute_share_gap_after_pp, "summary.mean_absolute_share_gap_after_pp"),
      spatial_imbalance_improvement_pct: asNumber(summary.spatial_imbalance_improvement_pct, "summary.spatial_imbalance_improvement_pct"),
    },
    validation: {
      status: validationStatus,
      constraints_passed: asBoolean(validation.constraints_passed, "validation.constraints_passed"),
      total_scooters_moved: asNumber(validation.total_scooters_moved, "validation.total_scooters_moved"),
      move_budget: asNumber(validation.move_budget, "validation.move_budget"),
      mean_absolute_share_gap_before_pp: asNumber(validation.mean_absolute_share_gap_before_pp, "validation.mean_absolute_share_gap_before_pp"),
      mean_absolute_share_gap_after_pp: asNumber(validation.mean_absolute_share_gap_after_pp, "validation.mean_absolute_share_gap_after_pp"),
      spatial_imbalance_improvement_pct: asNumber(validation.spatial_imbalance_improvement_pct, "validation.spatial_imbalance_improvement_pct"),
      errors: asArray(validation.errors, "validation.errors").map((error, index) => asString(error, `validation.errors[${index}]`)),
    },
    agent: {
      trace,
      recommendation: asString(agent.recommendation, "agent.recommendation"),
    },
  }
}

export async function refreshAnalysis(signal?: AbortSignal): Promise<AnalysisResult> {
  const response = await fetch("/api/analysis", {
    method: "POST",
    signal,
  })

  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Analysis request failed (${response.status})`)
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch (error) {
    const detail = error instanceof Error ? error.message : String(error)
    throw new Error(`Analysis response could not be parsed as JSON: ${detail}`)
  }

  return normalizeAnalysisResponse(payload)
}
