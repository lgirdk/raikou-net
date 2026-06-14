import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './theme.css'
import App from './App'

// Mount the React app onto the <div id="root"> in index.html.
// StrictMode runs each component twice in development to catch bugs early —
// it has no effect in the production build.
createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
