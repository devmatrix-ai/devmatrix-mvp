import { render, screen } from '@testing-library/react'
import ConfidenceIndicator from '../ConfidenceIndicator'

describe('ConfidenceIndicator', () => {
  it('displays high confidence with emerald color and correct icon', () => {
    render(<ConfidenceIndicator score={0.90} />)

    // Check label text contains score and level
    const label = screen.getByText('90% (high)')
    expect(label).toBeInTheDocument()

    // Check emerald color is applied
    expect(label).toHaveClass('text-emerald-400')
  })

  it('displays medium confidence with amber color', () => {
    render(<ConfidenceIndicator score={0.75} />)

    const label = screen.getByText('75% (medium)')
    expect(label).toBeInTheDocument()
    expect(label).toHaveClass('text-amber-400')
  })

  it('displays low confidence with orange color', () => {
    render(<ConfidenceIndicator score={0.60} />)

    const label = screen.getByText('60% (low)')
    expect(label).toBeInTheDocument()
    expect(label).toHaveClass('text-orange-500')
  })

  it('displays critical confidence with red color', () => {
    render(<ConfidenceIndicator score={0.40} />)

    const label = screen.getByText('40% (critical)')
    expect(label).toBeInTheDocument()
    expect(label).toHaveClass('text-red-500')
  })

  it('hides label when showLabel is false', () => {
    render(<ConfidenceIndicator score={0.85} showLabel={false} />)

    expect(screen.queryByText(/85%/)).not.toBeInTheDocument()
  })

  it('adjusts icon size based on size prop', () => {
    const { rerender } = render(<ConfidenceIndicator score={0.85} size="small" />)
    let icon = screen.getByText(/85%/).previousSibling as SVGElement
    expect(icon).toHaveAttribute('width', '16')

    rerender(<ConfidenceIndicator score={0.85} size="large" />)
    icon = screen.getByText(/85%/).previousSibling as SVGElement
    expect(icon).toHaveAttribute('width', '32')
  })
})
