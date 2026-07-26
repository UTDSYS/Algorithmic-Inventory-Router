import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, test } from 'vitest'
import { InfoPopover } from './InfoPopover'

describe('InfoPopover', () => {
  test('is closed by default', () => {
    render(
      <InfoPopover title="Scoring" label="How scoring works">
        Lower is better.
      </InfoPopover>,
    )
    expect(screen.queryByText('Lower is better.')).not.toBeInTheDocument()
  })

  test('opens on click and shows title and body', async () => {
    const user = userEvent.setup()
    render(
      <InfoPopover title="Scoring" label="How scoring works">
        Lower is better.
      </InfoPopover>,
    )
    await user.click(screen.getByRole('button', { name: 'How scoring works' }))
    expect(screen.getByText('Scoring')).toBeInTheDocument()
    expect(screen.getByText('Lower is better.')).toBeInTheDocument()
  })

  test('closes on Escape', async () => {
    const user = userEvent.setup()
    render(
      <InfoPopover title="Scoring" label="How scoring works">
        Lower is better.
      </InfoPopover>,
    )
    await user.click(screen.getByRole('button', { name: 'How scoring works' }))
    await user.keyboard('{Escape}')
    expect(screen.queryByText('Lower is better.')).not.toBeInTheDocument()
  })

  test('closes on outside click', async () => {
    const user = userEvent.setup()
    render(
      <div>
        <InfoPopover title="Scoring" label="How scoring works">
          Lower is better.
        </InfoPopover>
        <button>outside</button>
      </div>,
    )
    await user.click(screen.getByRole('button', { name: 'How scoring works' }))
    expect(screen.getByText('Lower is better.')).toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'outside' }))
    expect(screen.queryByText('Lower is better.')).not.toBeInTheDocument()
  })

  test('toggles aria-expanded', async () => {
    const user = userEvent.setup()
    render(
      <InfoPopover title="Scoring" label="How scoring works">
        Lower is better.
      </InfoPopover>,
    )
    const trigger = screen.getByRole('button', { name: 'How scoring works' })
    expect(trigger).toHaveAttribute('aria-expanded', 'false')
    await user.click(trigger)
    expect(trigger).toHaveAttribute('aria-expanded', 'true')
  })
})
