import { StrictMode, Suspense } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import './i18n' // Initialize i18n
import App from './App.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <Suspense fallback={<div className="flex items-center justify-center h-screen bg-mesh"><div className="text-white">Loading...</div></div>}>
      <App />
    </Suspense>
  </StrictMode>,
)
