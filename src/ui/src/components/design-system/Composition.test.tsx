import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { GlassCard } from './GlassCard'
import { GlassButton } from './GlassButton'
import { StatusBadge } from './StatusBadge'
import { PageHeader } from './PageHeader'
import { SectionHeader } from './SectionHeader'

describe('Component Composition', () => {
  it('renders GlassCard with GlassButton and StatusBadge', () => {
    render(
      <GlassCard>
        <SectionHeader>Test Card</SectionHeader>
        <StatusBadge status="success">Active</StatusBadge>
        <GlassButton variant="primary">Action</GlassButton>
      </GlassCard>
    )

    expect(screen.getByText('Test Card')).toBeInTheDocument()
    expect(screen.getByText('Active')).toBeInTheDocument()
    expect(screen.getByText('Action')).toBeInTheDocument()
  })

  it('renders PageHeader with multiple child components in GlassCard', () => {
    render(
      <>
        <PageHeader emoji="🎯" title="Dashboard" subtitle="System overview" />
        <GlassCard hover>
          <StatusBadge status="success">Online</StatusBadge>
          <GlassButton variant="secondary">Details</GlassButton>
        </GlassCard>
      </>
    )

    expect(screen.getByText('🎯')).toBeInTheDocument()
    expect(screen.getByText('Dashboard')).toBeInTheDocument()
    expect(screen.getByText('System overview')).toBeInTheDocument()
    expect(screen.getByText('Online')).toBeInTheDocument()
    expect(screen.getByText('Details')).toBeInTheDocument()
  })
})
