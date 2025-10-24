/**
 * Design System Demo - Visual Reference
 *
 * This file demonstrates all core design system components.
 * Use this for visual testing and as a reference implementation.
 */

import React from 'react'
import { GlassCard, GlassButton, StatusBadge } from './index'

export const DesignSystemDemo: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-blue-900/20 p-8">
      <div className="max-w-4xl mx-auto space-y-8">
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-4">
            <div className="text-5xl">🎨</div>
            <h1 className="text-4xl font-bold text-white">Design System</h1>
          </div>
          <p className="text-gray-400 text-lg">
            Glassmorphism components for DevMatrix
          </p>
        </div>

        {/* GlassCard Examples */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">GlassCard</h2>

          <GlassCard>
            <h3 className="text-xl font-semibold text-white mb-2">Basic Card</h3>
            <p className="text-gray-300">
              A basic glassmorphism card with backdrop blur and gradient borders.
            </p>
          </GlassCard>

          <GlassCard hover>
            <h3 className="text-xl font-semibold text-white mb-2">Card with Hover Effect</h3>
            <p className="text-gray-300">
              This card has a hover shadow effect. Try hovering over it!
            </p>
          </GlassCard>

          <GlassCard className="max-w-md">
            <h3 className="text-xl font-semibold text-white mb-2">Custom Width Card</h3>
            <p className="text-gray-300">
              Cards can be customized with additional classes.
            </p>
          </GlassCard>
        </div>

        {/* GlassButton Examples */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">GlassButton</h2>

          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4">Button Variants</h3>
            <div className="flex flex-wrap gap-3">
              <GlassButton variant="primary">Primary</GlassButton>
              <GlassButton variant="secondary">Secondary</GlassButton>
              <GlassButton variant="ghost">Ghost</GlassButton>
              <GlassButton variant="primary" disabled>Disabled</GlassButton>
            </div>
          </GlassCard>

          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4">Button Sizes</h3>
            <div className="flex flex-wrap items-center gap-3">
              <GlassButton size="sm">Small</GlassButton>
              <GlassButton size="md">Medium</GlassButton>
              <GlassButton size="lg">Large</GlassButton>
            </div>
          </GlassCard>
        </div>

        {/* StatusBadge Examples */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">StatusBadge</h2>

          <GlassCard>
            <h3 className="text-lg font-semibold text-white mb-4">Status Types</h3>
            <div className="flex flex-wrap gap-3">
              <StatusBadge status="success">Success</StatusBadge>
              <StatusBadge status="warning">Warning</StatusBadge>
              <StatusBadge status="error">Error</StatusBadge>
              <StatusBadge status="info">Info</StatusBadge>
              <StatusBadge status="default">Default</StatusBadge>
            </div>
          </GlassCard>
        </div>

        {/* Complex Example */}
        <div className="space-y-4">
          <h2 className="text-2xl font-bold text-white">Component Composition</h2>

          <GlassCard hover>
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-xl font-semibold text-white mb-2">Project Dashboard</h3>
                <p className="text-gray-400">Manage your development workflow</p>
              </div>
              <StatusBadge status="success">Active</StatusBadge>
            </div>

            <div className="space-y-4">
              <div className="flex gap-3">
                <GlassButton variant="primary" size="md">
                  Start Project
                </GlassButton>
                <GlassButton variant="secondary" size="md">
                  View Details
                </GlassButton>
                <GlassButton variant="ghost" size="md">
                  Settings
                </GlassButton>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>
    </div>
  )
}
