import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { MovedTo } from './components/MovedTo'
import { RouteLoading } from './components/RouteLoading'
import { EmbedBoundary } from './embed/EmbedBoundary'
import AboutPage from './pages/AboutPage'
import NotFoundPage from './pages/NotFoundPage'
import OverviewPage from './pages/OverviewPage'

// Every page but the overview loads on demand: its code (and the data it fetches) stays out of the first download.
const TopicsPage = lazy(() => import('./pages/TopicsPage'))
const TopicPage = lazy(() => import('./pages/TopicPage'))
const PlacesPage = lazy(() => import('./pages/PlacesPage'))
const InstitutionPage = lazy(() => import('./pages/InstitutionPage'))
const ProvincePage = lazy(() => import('./pages/ProvincePage'))
const JournalsPage = lazy(() => import('./pages/JournalsPage'))
const JournalPage = lazy(() => import('./pages/JournalPage'))
const GoalsPage = lazy(() => import('./pages/GoalsPage'))
const AtlasPage = lazy(() => import('./pages/AtlasPage'))
const GalaxyPage = lazy(() => import('./pages/GalaxyPage'))
// Embeddable widgets (iframe) render without the site's sidebar and footer.
const EmbedTopic = lazy(() => import('./embed/EmbedTopic'))
const EmbedEmerging = lazy(() => import('./embed/EmbedEmerging'))

function Lazy({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteLoading />}>{children}</Suspense>
}

/**
 * Five dashboards (overview, topics, places, journals, goals), their detail pages and the two maps. Pages retired in the
 * 2026-10-24 dashboard redesign send old links (feeds, shared URLs) to the dashboard that now carries their content.
 */
export default function App() {
  return (
    <Routes>
      <Route path="/embed/topic/:id" element={<EmbedBoundary><Lazy><EmbedTopic /></Lazy></EmbedBoundary>} />
      <Route path="/embed/emerging" element={<EmbedBoundary><Lazy><EmbedEmerging /></Lazy></EmbedBoundary>} />
      <Route path="/embed/*" element={<EmbedBoundary><Lazy><EmbedTopic /></Lazy></EmbedBoundary>} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="topics" element={<Lazy><TopicsPage /></Lazy>} />
        <Route path="topics/:id" element={<Lazy><TopicPage /></Lazy>} />
        <Route path="places" element={<Lazy><PlacesPage /></Lazy>} />
        <Route path="institutions/:id" element={<Lazy><InstitutionPage /></Lazy>} />
        <Route path="province/:code" element={<Lazy><ProvincePage /></Lazy>} />
        <Route path="journals" element={<Lazy><JournalsPage /></Lazy>} />
        <Route path="journals/:id" element={<Lazy><JournalPage /></Lazy>} />
        <Route path="goals" element={<Lazy><GoalsPage /></Lazy>} />
        <Route path="atlas" element={<Lazy><AtlasPage /></Lazy>} />
        <Route path="galaxy" element={<Lazy><GalaxyPage /></Lazy>} />
        <Route path="about" element={<AboutPage />} />
        {/* retired pages → the dashboard that carries their content (the status filter of /emerging carries over) */}
        <Route path="emerging" element={<MovedTo to="/topics" keepQuery />} />
        <Route path="changes" element={<MovedTo to="/topics" />} />
        <Route path="gaps" element={<MovedTo to="/topics" />} />
        <Route path="ideas" element={<MovedTo to="/topics" />} />
        <Route path="keywords" element={<MovedTo to="/topics" />} />
        <Route path="story" element={<MovedTo to="/overview" />} />
        <Route path="brief" element={<MovedTo to="/overview" />} />
        <Route path="institutions" element={<MovedTo to="/places" />} />
        <Route path="regions" element={<MovedTo to="/places" />} />
        <Route path="province" element={<MovedTo to="/places" />} />
        <Route path="methods" element={<MovedTo to="/journals" />} />
        <Route path="references" element={<MovedTo to="/journals" />} />
        <Route path="sdg" element={<MovedTo to="/goals" />} />
        <Route path="global" element={<MovedTo to="/goals" />} />
        <Route path="search" element={<MovedTo to="/overview" />} />
        <Route path="compare" element={<MovedTo to="/overview" />} />
        <Route path="match" element={<MovedTo to="/overview" />} />
        <Route path="data" element={<MovedTo to="/overview" />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
