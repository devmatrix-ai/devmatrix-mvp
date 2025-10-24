import { render, screen, fireEvent } from '@testing-library/react'
import { CustomAccordion } from '../CustomAccordion'
import { FiCode } from 'react-icons/fi'

describe('CustomAccordion', () => {
  it('renders with title', () => {
    render(
      <CustomAccordion title="Test Accordion">
        <div>Content</div>
      </CustomAccordion>
    )

    expect(screen.getByText('Test Accordion')).toBeInTheDocument()
  })

  it('starts collapsed by default', () => {
    render(
      <CustomAccordion title="Test">
        <div>Hidden Content</div>
      </CustomAccordion>
    )

    expect(screen.queryByText('Hidden Content')).not.toBeInTheDocument()
  })

  it('starts expanded when defaultExpanded is true', () => {
    render(
      <CustomAccordion title="Test" defaultExpanded>
        <div>Visible Content</div>
      </CustomAccordion>
    )

    expect(screen.getByText('Visible Content')).toBeInTheDocument()
  })

  it('expands when clicked', () => {
    render(
      <CustomAccordion title="Test">
        <div>Content</div>
      </CustomAccordion>
    )

    const button = screen.getByRole('button')
    fireEvent.click(button)

    expect(screen.getByText('Content')).toBeInTheDocument()
  })

  it('collapses when clicked twice', () => {
    render(
      <CustomAccordion title="Test" defaultExpanded>
        <div>Content</div>
      </CustomAccordion>
    )

    const button = screen.getByRole('button')
    expect(screen.getByText('Content')).toBeInTheDocument()

    fireEvent.click(button)
    expect(screen.queryByText('Content')).not.toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    render(
      <CustomAccordion title="Test" icon={<FiCode data-testid="icon" />}>
        <div>Content</div>
      </CustomAccordion>
    )

    expect(screen.getByTestId('icon')).toBeInTheDocument()
  })

  it('has correct aria-expanded attribute', () => {
    render(
      <CustomAccordion title="Test">
        <div>Content</div>
      </CustomAccordion>
    )

    const button = screen.getByRole('button')
    expect(button).toHaveAttribute('aria-expanded', 'false')

    fireEvent.click(button)
    expect(button).toHaveAttribute('aria-expanded', 'true')
  })
})
