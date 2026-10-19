import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { RouteLoading } from './components/RouteLoading'
import AboutPage from './pages/AboutPage'
import AtlasPage from './pages/AtlasPage'
import BriefPage from './pages/BriefPage'
import ComparePage from './pages/ComparePage'
import DataPage from './pages/DataPage'
import EmergingPage from './pages/EmergingPage'
import NotFoundPage from './pages/NotFoundPage'
import OverviewPage from './pages/OverviewPage'
import TopicPage from './pages/TopicPage'

// The editors' pages load on demand: their code (and the data they fetch) stays out of the first download.
const JournalsPage = lazy(() => import('./pages/JournalsPage'))
const JournalPage = lazy(() => import('./pages/JournalPage'))
const MethodsPage = lazy(() => import('./pages/MethodsPage'))
const ChangesPage = lazy(() => import('./pages/ChangesPage'))
const MatchPage = lazy(() => import('./pages/MatchPage'))

function Lazy({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteLoading />}>{children}</Suspense>
}

export default function App() {
  return (
    <Routes>
      <Route path="/brief" element={<BriefPage />} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="atlas" element={<AtlasPage />} />
        <Route path="topics/:id" element={<TopicPage />} />
        <Route path="emerging" element={<EmergingPage />} />
        <Route path="journals" element={<Lazy><JournalsPage /></Lazy>} />
        <Route path="journals/:id" element={<Lazy><JournalPage /></Lazy>} />
        <Route path="methods" element={<Lazy><MethodsPage /></Lazy>} />
        <Route path="changes" element={<Lazy><ChangesPage /></Lazy>} />
        <Route path="match" element={<Lazy><MatchPage /></Lazy>} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
