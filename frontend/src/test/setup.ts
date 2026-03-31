import '@testing-library/jest-dom'
import { vi } from 'vitest'

// Mock de ResizeObserver que o React Flow precisa no JSDOM
class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

window.ResizeObserver = ResizeObserver
