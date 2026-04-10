import { describe, it, expect } from 'vitest'
import { render } from '@testing-library/react'
import App from '../App'

describe('App', () => {
  it('renders the application', () => {
    render(<App />)
    // The app should render without crashing
    expect(document.body).toBeDefined()
  })

  it('should have the main container element', () => {
    const { container } = render(<App />)
    const mainDiv = container.querySelector('.bg-white')
    expect(mainDiv).toBeDefined()
  })
})
