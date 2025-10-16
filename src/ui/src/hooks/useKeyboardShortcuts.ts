import { useEffect } from 'react'

interface KeyboardShortcut {
  key: string
  ctrlKey?: boolean
  metaKey?: boolean
  shiftKey?: boolean
  altKey?: boolean
  handler: () => void
  description: string
}

interface UseKeyboardShortcutsOptions {
  enabled?: boolean
}

export function useKeyboardShortcuts(
  shortcuts: KeyboardShortcut[],
  options: UseKeyboardShortcutsOptions = {}
) {
  const { enabled = true } = options

  useEffect(() => {
    if (!enabled) return

    const handleKeyDown = (e: KeyboardEvent) => {
      // Don't trigger shortcuts if user is typing in an input
      const target = e.target as HTMLElement
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        // Allow some shortcuts even in inputs (like Ctrl+S)
        const allowedInInputs = shortcuts.filter(
          (s) => s.ctrlKey || s.metaKey
        )
        const matchesAllowed = allowedInInputs.find(
          (shortcut) =>
            shortcut.key.toLowerCase() === e.key.toLowerCase() &&
            (shortcut.ctrlKey === e.ctrlKey ||
              shortcut.metaKey === e.metaKey) &&
            (shortcut.shiftKey === undefined ||
              shortcut.shiftKey === e.shiftKey) &&
            (shortcut.altKey === undefined || shortcut.altKey === e.altKey)
        )

        if (!matchesAllowed) return
      }

      // Find matching shortcut
      const matchingShortcut = shortcuts.find(
        (shortcut) =>
          shortcut.key.toLowerCase() === e.key.toLowerCase() &&
          (shortcut.ctrlKey === undefined || shortcut.ctrlKey === e.ctrlKey) &&
          (shortcut.metaKey === undefined || shortcut.metaKey === e.metaKey) &&
          (shortcut.shiftKey === undefined ||
            shortcut.shiftKey === e.shiftKey) &&
          (shortcut.altKey === undefined || shortcut.altKey === e.altKey)
      )

      if (matchingShortcut) {
        e.preventDefault()
        matchingShortcut.handler()
      }
    }

    document.addEventListener('keydown', handleKeyDown)

    return () => {
      document.removeEventListener('keydown', handleKeyDown)
    }
  }, [shortcuts, enabled])

  return { shortcuts }
}

/**
 * Format shortcut for display (e.g., "Ctrl+K" or "⌘+K" on Mac)
 */
export function formatShortcut(shortcut: KeyboardShortcut): string {
  const isMac = navigator.platform.toUpperCase().indexOf('MAC') >= 0
  const parts: string[] = []

  if (shortcut.ctrlKey || shortcut.metaKey) {
    parts.push(isMac ? '⌘' : 'Ctrl')
  }
  if (shortcut.shiftKey) {
    parts.push(isMac ? '⇧' : 'Shift')
  }
  if (shortcut.altKey) {
    parts.push(isMac ? '⌥' : 'Alt')
  }
  parts.push(shortcut.key.toUpperCase())

  return parts.join('+')
}
