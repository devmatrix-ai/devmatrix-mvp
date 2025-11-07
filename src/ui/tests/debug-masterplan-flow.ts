/**
 * debug-masterplan-flow.ts
 *
 * Debug utility to trace the complete MasterPlan progress flow
 * from WebSocket events to UI rendering.
 *
 * Usage in console:
 * ```
 * import { setupMasterPlanDebugger } from './debug-masterplan-flow'
 * setupMasterPlanDebugger()
 * ```
 *
 * This will log:
 * - All WebSocket events with timestamps
 * - useMasterPlanProgress state changes
 * - Zustand store updates
 * - Component renders
 * - Data integrity checks
 */

interface DebugEvent {
  timestamp: number
  layer: 'websocket' | 'useChat' | 'useMasterPlanProgress' | 'zustand' | 'component'
  eventType: string
  data: any
  sessionId?: string
  _dataHash?: string // For deduplication detection
}

interface FlowTrace {
  events: DebugEvent[]
  sessionIds: Set<string>
  eventCounts: Record<string, number>
  issues: string[]
}

const flowTrace: FlowTrace = {
  events: [],
  sessionIds: new Set(),
  eventCounts: {},
  issues: [],
}

// ═══════════════════════════════════════════════════════════════════════════════
// 1. WEBSOCKET LAYER - Intercept raw events
// ═══════════════════════════════════════════════════════════════════════════════

function setupWebSocketInterception() {
  console.log('🔍 [Debugger] Setting up WebSocket interception...')

  // Find the WebSocket context in window
  const interceptWebSocketContext = () => {
    // This is a bit hacky - we're trying to monitor the event emissions
    // In a real scenario, you'd instrument the WebSocket hook directly

    const originalFetch = window.fetch
    const originalWS = (window as any).WebSocket

    // Patch fetch to monitor WebSocket-related calls
    ;(window as any).fetch = function (...args: any[]) {
      const url = args[0]
      if (url && typeof url === 'string' && url.includes('/ws')) {
        console.log('[Debugger::WebSocket] WS Fetch call:', url, args[1])
      }
      return originalFetch.apply(this, args)
    }

    console.log('✅ WebSocket context intercepted')
  }

  interceptWebSocketContext()
}

// ═══════════════════════════════════════════════════════════════════════════════
// 2. useChat LAYER - Monitor event listener registration
// ═══════════════════════════════════════════════════════════════════════════════

function setupUseChatInterception() {
  console.log('🔍 [Debugger] Setting up useChat event listener monitoring...')

  // Patch console.log to capture useChat debug logs
  const originalLog = console.log
  const useChatLogs: string[] = []

  ;(window as any).__masterplanDebug = {
    useChatLogs,
    captureUseChatEvent: (event: string, data: any) => {
      const debugEvent: DebugEvent = {
        timestamp: Date.now(),
        layer: 'useChat',
        eventType: event,
        data,
        sessionId: data?.session_id || data?.masterplan_id || undefined,
      }

      flowTrace.events.push(debugEvent)
      if (debugEvent.sessionId) {
        flowTrace.sessionIds.add(debugEvent.sessionId)
      }

      // Track event counts
      flowTrace.eventCounts[event] = (flowTrace.eventCounts[event] || 0) + 1

      console.log(
        `📤 [useChat] ${event}`,
        {
          sessionId: debugEvent.sessionId,
          dataKeys: Object.keys(data || {}),
          timestamp: new Date(debugEvent.timestamp).toISOString(),
        },
        data
      )
    },
  }

  console.log('✅ useChat event listener monitoring enabled')
}

// ═══════════════════════════════════════════════════════════════════════════════
// 3. useMasterPlanProgress LAYER - Monitor state machine transitions
// ═══════════════════════════════════════════════════════════════════════════════

function setupUseMasterPlanProgressInterception() {
  console.log('🔍 [Debugger] Setting up useMasterPlanProgress state monitoring...')

  ;(window as any).__masterplanDebug = {
    ...(window as any).__masterplanDebug,
    progressStates: [],
    captureProgressState: (state: any, event: string, sessionId: string) => {
      const debugEvent: DebugEvent = {
        timestamp: Date.now(),
        layer: 'useMasterPlanProgress',
        eventType: event,
        data: {
          percentage: state.percentage,
          tokensReceived: state.tokensReceived,
          estimatedTotalTokens: state.estimatedTotalTokens,
          currentPhase: state.currentPhase,
          isComplete: state.isComplete,
          boundedContexts: state.boundedContexts,
          aggregates: state.aggregates,
          entities: state.entities,
          phasesFound: state.phasesFound,
          milestonesFound: state.milestonesFound,
          tasksFound: state.tasksFound,
          cost: state.cost,
          elapsedSeconds: state.elapsedSeconds,
        },
        sessionId,
      }

      flowTrace.events.push(debugEvent)
      ;(window as any).__masterplanDebug.progressStates.push(debugEvent)

      // Check for data consistency
      if (
        state.percentage > 100 ||
        state.percentage < 0 ||
        isNaN(state.percentage)
      ) {
        const issue = `❌ Invalid percentage: ${state.percentage} for event ${event}`
        flowTrace.issues.push(issue)
        console.warn(issue)
      }

      if (state.tokensReceived > state.estimatedTotalTokens) {
        const issue = `⚠️ Tokens received (${state.tokensReceived}) > estimated (${state.estimatedTotalTokens})`
        flowTrace.issues.push(issue)
        console.warn(issue)
      }

      console.log(
        `📊 [useMasterPlanProgress] ${event}`,
        {
          percentage: state.percentage,
          phase: state.currentPhase,
          tokens: `${state.tokensReceived}/${state.estimatedTotalTokens}`,
          entities: {
            bc: state.boundedContexts,
            agg: state.aggregates,
            ent: state.entities,
            ph: state.phasesFound,
            ms: state.milestonesFound,
            tk: state.tasksFound,
          },
          isComplete: state.isComplete,
          sessionId,
        }
      )
    },
  }

  console.log('✅ useMasterPlanProgress state monitoring enabled')
}

// ═══════════════════════════════════════════════════════════════════════════════
// 4. ZUSTAND LAYER - Monitor store updates
// ═══════════════════════════════════════════════════════════════════════════════

function setupZustandInterception() {
  console.log('🔍 [Debugger] Setting up Zustand store monitoring...')

  ;(window as any).__masterplanDebug = {
    ...(window as any).__masterplanDebug,
    storeUpdates: [],
    captureStoreUpdate: (action: string, data: any) => {
      const debugEvent: DebugEvent = {
        timestamp: Date.now(),
        layer: 'zustand',
        eventType: action,
        data,
      }

      flowTrace.events.push(debugEvent)
      ;(window as any).__masterplanDebug.storeUpdates.push(debugEvent)

      console.log(
        `💾 [Zustand] ${action}`,
        {
          keys: Object.keys(data || {}),
          timestamp: new Date(debugEvent.timestamp).toISOString(),
        },
        data
      )
    },
  }

  console.log('✅ Zustand store monitoring enabled')
}

// ═══════════════════════════════════════════════════════════════════════════════
// 5. COMPONENT RENDER LAYER - Monitor component updates
// ═══════════════════════════════════════════════════════════════════════════════

function setupComponentRenderInterception() {
  console.log('🔍 [Debugger] Setting up component render monitoring...')

  ;(window as any).__masterplanDebug = {
    ...(window as any).__masterplanDebug,
    componentRenders: [],
    captureComponentRender: (component: string, props: any) => {
      const debugEvent: DebugEvent = {
        timestamp: Date.now(),
        layer: 'component',
        eventType: component,
        data: {
          propKeys: Object.keys(props || {}),
          props: JSON.stringify(props, null, 2).substring(0, 500), // Limit size
        },
      }

      flowTrace.events.push(debugEvent)
      ;(window as any).__masterplanDebug.componentRenders.push(debugEvent)

      console.log(`🎨 [Component] ${component}`, {
        propKeys: Object.keys(props || {}),
        timestamp: new Date(debugEvent.timestamp).toISOString(),
      })
    },
  }

  console.log('✅ Component render monitoring enabled')
}

// ═══════════════════════════════════════════════════════════════════════════════
// 6. ANALYSIS & REPORTING
// ═══════════════════════════════════════════════════════════════════════════════

function analyzeFlow() {
  console.log('\n' + '═'.repeat(80))
  console.log('📊 MASTERPLAN PROGRESS FLOW ANALYSIS')
  console.log('═'.repeat(80))

  // Timeline analysis
  if (flowTrace.events.length > 0) {
    const firstEvent = flowTrace.events[0]
    const lastEvent = flowTrace.events[flowTrace.events.length - 1]
    const duration = lastEvent.timestamp - firstEvent.timestamp

    console.log('\n⏱️  TIMELINE')
    console.log(`  Start: ${new Date(firstEvent.timestamp).toISOString()}`)
    console.log(`  End:   ${new Date(lastEvent.timestamp).toISOString()}`)
    console.log(`  Total Duration: ${duration}ms (${(duration / 1000).toFixed(2)}s)`)
  }

  // Event count analysis
  console.log('\n📈 EVENT COUNTS')
  const sortedEvents = Object.entries(flowTrace.eventCounts).sort(
    ([, a], [, b]) => b - a
  )
  sortedEvents.forEach(([event, count]) => {
    console.log(`  ${event}: ${count}`)
  })

  // Session ID analysis
  console.log('\n🔑 SESSION IDS')
  flowTrace.sessionIds.forEach(id => {
    const count = flowTrace.events.filter(e => e.sessionId === id).length
    console.log(`  ${id}: ${count} events`)
  })

  // Event flow by layer
  console.log('\n📍 EVENT FLOW BY LAYER')
  const byLayer = {
    websocket: flowTrace.events.filter(e => e.layer === 'websocket').length,
    useChat: flowTrace.events.filter(e => e.layer === 'useChat').length,
    useMasterPlanProgress: flowTrace.events.filter(
      e => e.layer === 'useMasterPlanProgress'
    ).length,
    zustand: flowTrace.events.filter(e => e.layer === 'zustand').length,
    component: flowTrace.events.filter(e => e.layer === 'component').length,
  }

  Object.entries(byLayer).forEach(([layer, count]) => {
    console.log(`  ${layer}: ${count}`)
  })

  // Issues found
  if (flowTrace.issues.length > 0) {
    console.log('\n⚠️  ISSUES FOUND')
    flowTrace.issues.forEach(issue => {
      console.log(`  ${issue}`)
    })
  } else {
    console.log('\n✅ No data integrity issues detected')
  }

  // Synchronization check
  console.log('\n🔄 SYNCHRONIZATION CHECK')
  const discoveryEvents = Object.entries(flowTrace.eventCounts).filter(
    ([key]) => key.includes('discovery')
  )
  const masterplanEvents = Object.entries(flowTrace.eventCounts).filter(
    ([key]) => key.includes('masterplan')
  )

  console.log(`  Discovery events: ${discoveryEvents.reduce((sum, [, count]) => sum + count, 0)}`)
  console.log(`  MasterPlan events: ${masterplanEvents.reduce((sum, [, count]) => sum + count, 0)}`)

  // Check for event sequence
  const eventSequence = flowTrace.events.map(e => e.eventType)
  const hasDiscoveryStart = eventSequence.includes('discovery_generation_start')
  const hasDiscoveryComplete = eventSequence.includes('discovery_generation_complete')
  const hasMasterplanStart = eventSequence.includes('masterplan_generation_start')
  const hasMasterplanComplete = eventSequence.includes('masterplan_generation_complete')

  console.log('\n✓ EVENT SEQUENCE')
  console.log(`  ${hasDiscoveryStart ? '✅' : '❌'} discovery_generation_start`)
  console.log(`  ${hasDiscoveryComplete ? '✅' : '❌'} discovery_generation_complete`)
  console.log(`  ${hasMasterplanStart ? '✅' : '❌'} masterplan_generation_start`)
  console.log(`  ${hasMasterplanComplete ? '✅' : '❌'} masterplan_generation_complete`)

  // Export raw data for further analysis
  console.log('\n💾 EXPORT FLOW DATA')
  console.log('  Use: window.__masterplanDebug.exportFlow()')
  ;(window as any).__masterplanDebug.exportFlow = () => {
    const data = {
      summary: {
        totalEvents: flowTrace.events.length,
        duration: flowTrace.events.length > 0
          ? flowTrace.events[flowTrace.events.length - 1].timestamp -
            flowTrace.events[0].timestamp
          : 0,
        sessionIds: Array.from(flowTrace.sessionIds),
        eventCounts: flowTrace.eventCounts,
        issues: flowTrace.issues,
      },
      events: flowTrace.events,
    }
    console.log(JSON.stringify(data, null, 2))
    return data
  }

  console.log('\n' + '═'.repeat(80))
}

// ═══════════════════════════════════════════════════════════════════════════════
// 7. MAIN SETUP FUNCTION
// ═══════════════════════════════════════════════════════════════════════════════

export function setupMasterPlanDebugger() {
  console.log('\n' + '🔧'.repeat(40))
  console.log('MASTERPLAN PROGRESS DEBUGGER INITIALIZED')
  console.log('🔧'.repeat(40) + '\n')

  // Setup all interception layers
  setupWebSocketInterception()
  setupUseChatInterception()
  setupUseMasterPlanProgressInterception()
  setupZustandInterception()
  setupComponentRenderInterception()

  // Export analysis function
  ;(window as any).__masterplanDebug = {
    ...(window as any).__masterplanDebug,
    analyze: analyzeFlow,
    getFlowTrace: () => flowTrace,
    clearFlowTrace: () => {
      flowTrace.events = []
      flowTrace.sessionIds.clear()
      flowTrace.eventCounts = {}
      flowTrace.issues = []
    },
  }

  console.log('✅ Debugger ready! Use __masterplanDebug.analyze() for report\n')

  // Auto-analyze after 5 seconds
  setTimeout(() => {
    console.log('\n🤖 Running automatic analysis...\n')
    analyzeFlow()
  }, 5000)
}

// ═══════════════════════════════════════════════════════════════════════════════
// 8. QUICK INSPECTION COMMANDS
// ═══════════════════════════════════════════════════════════════════════════════

export function getQuickReport() {
  return {
    totalEvents: flowTrace.events.length,
    lastEvent: flowTrace.events[flowTrace.events.length - 1],
    eventTypes: Object.keys(flowTrace.eventCounts),
    issues: flowTrace.issues,
    sessionIds: Array.from(flowTrace.sessionIds),
  }
}

// Auto-setup on import if in development
if (process.env.NODE_ENV === 'development') {
  if (typeof window !== 'undefined') {
    // Delay setup to ensure app is ready
    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', setupMasterPlanDebugger)
    } else {
      setTimeout(setupMasterPlanDebugger, 1000)
    }
  }
}
