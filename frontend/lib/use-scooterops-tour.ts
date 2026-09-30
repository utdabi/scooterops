"use client"

import { useCallback, useEffect, useRef } from "react"
import { driver, type Driver } from "driver.js"

const TOUR_STORAGE_KEY = "scooterops-tour-seen"

interface UseScooterOpsTourOptions {
  isDashboardReady: boolean
  showProposedRoutes: () => void
}

export function useScooterOpsTour({ isDashboardReady, showProposedRoutes }: UseScooterOpsTourOptions) {
  const activeTour = useRef<Driver | null>(null)
  const hasCheckedFirstVisit = useRef(false)

  const startTour = useCallback(() => {
    activeTour.current?.destroy()

    const tour = driver({
      animate: true,
      overlayColor: "#030405",
      overlayOpacity: 0.72,
      stagePadding: 8,
      stageRadius: 8,
      smoothScroll: true,
      allowClose: true,
      showProgress: true,
      progressText: "{{current}} / {{total}}",
      nextBtnText: "Next",
      prevBtnText: "Back",
      doneBtnText: "Finish",
      popoverClass: "scooterops-tour-popover",
      onDestroyed: () => {
        activeTour.current = null
      },
      steps: [
        {
          element: '[data-tour="fleet-map"]',
          popover: {
            title: "Live fleet map",
            description: "Live Lime scooter supply and fall seasonal demand shares are mapped across Chicago community areas.",
            side: "bottom",
            align: "start",
          },
        },
        {
          element: '[data-tour="supply-demand-gap"]',
          popover: {
            title: "Supply-demand gap",
            description: "Seasonal predicted demand share is compared with current fleet supply share to identify under- and over-supplied areas.",
            side: "bottom",
            align: "end",
          },
        },
        {
          element: '[data-tour="agent-trace"]',
          popover: {
            title: "Autonomous agent",
            description: "Amazon Bedrock orchestrates live fleet analysis, seasonal demand-share optimization, and independent plan validation.",
            side: "left",
            align: "start",
          },
        },
        {
          element: '[data-tour="movement-routes"]',
          onHighlightStarted: showProposedRoutes,
          popover: {
            title: "Optimized movements",
            description: "The MILP optimizer selects scooter movements under a 50-scooter rebalancing budget.",
            side: "left",
            align: "center",
          },
        },
        {
          element: '[data-tour="impact-metrics"]',
          popover: {
            title: "Measured impact",
            description: "The proposed plan reports mean share gaps before and after, plus measured spatial imbalance improvement.",
            side: "top",
            align: "start",
          },
        },
      ],
    })

    activeTour.current = tour
    tour.drive()
  }, [showProposedRoutes])

  useEffect(() => {
    if (!isDashboardReady || hasCheckedFirstVisit.current) return

    const frame = window.requestAnimationFrame(() => {
      if (hasCheckedFirstVisit.current) return
      hasCheckedFirstVisit.current = true

      try {
        if (window.localStorage.getItem(TOUR_STORAGE_KEY)) return
        window.localStorage.setItem(TOUR_STORAGE_KEY, "true")
      } catch {
        // Continue once per mounted session when storage is unavailable.
      }

      startTour()
    })

    return () => window.cancelAnimationFrame(frame)
  }, [isDashboardReady, startTour])

  useEffect(() => {
    return () => activeTour.current?.destroy()
  }, [])

  return startTour
}
