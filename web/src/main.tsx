import { TooltipProvider } from './components/TooltipProvider'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router'
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { ErrorFailure } from './components/ErrorFailure'
import { AtlasProvider } from './data/AtlasProvider'
import { sourceFromEmbeddedText } from './data/source'
import { syncDocumentLang } from './lib/i18n'
import './styles/index.css'

syncDocumentLang()
// The offline file carries the release in <script id="atlas-data">; on Pages the slot is "null" → fetch ./data/…
const source = sourceFromEmbeddedText(document.getElementById('atlas-data')?.textContent, import.meta.env.BASE_URL)

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    {/* Page state lives in the URL and drives controlled inputs (checkboxes, radios, the gazetteer search box): a location
        update inside startTransition would snap them back until it commits, so URL updates render synchronously. */}
    {/* the last line of defence: a failure in the site's header, menu, banners or footer (outside the page-area
        boundary in Layout) shows a reload message instead of a white page */}
    <ErrorBoundary fallback={(chunk) => <ErrorFailure chunk={chunk} shell />}>
      <HashRouter useTransitions={false}>
        <AtlasProvider source={source}>
          <TooltipProvider>
            <App />
          </TooltipProvider>
        </AtlasProvider>
      </HashRouter>
    </ErrorBoundary>
  </StrictMode>,
)
