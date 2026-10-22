import { lazy, Suspense, type ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import { RouteLoading } from './components/RouteLoading'
import AboutPage from './pages/AboutPage'
import ComparePage from './pages/ComparePage'
import DataPage from './pages/DataPage'
import EmergingPage from './pages/EmergingPage'
import NotFoundPage from './pages/NotFoundPage'
import OverviewPage from './pages/OverviewPage'
import TopicPage from './pages/TopicPage'

// The map (its terrain code) and the printable brief load on demand too: neither is needed for the first page.
const AtlasPage = lazy(() => import('./pages/AtlasPage'))
const BriefPage = lazy(() => import('./pages/BriefPage'))
// Embeddable widgets (iframe) render without the site's header, navigation and footer.
const EmbedTopic = lazy(() => import('./embed/EmbedTopic'))
const EmbedEmerging = lazy(() => import('./embed/EmbedEmerging'))
// The editors' pages load on demand: their code (and the data they fetch) stays out of the first download.
const JournalsPage = lazy(() => import('./pages/JournalsPage'))
const JournalPage = lazy(() => import('./pages/JournalPage'))
const MethodsPage = lazy(() => import('./pages/MethodsPage'))
const ChangesPage = lazy(() => import('./pages/ChangesPage'))
const MatchPage = lazy(() => import('./pages/MatchPage'))
// The executives' pages (P3), also on demand.
const InstitutionsPage = lazy(() => import('./pages/InstitutionsPage'))
const InstitutionPage = lazy(() => import('./pages/InstitutionPage'))
const RegionsPage = lazy(() => import('./pages/RegionsPage'))
const SdgPage = lazy(() => import('./pages/SdgPage'))
const GlobalPage = lazy(() => import('./pages/GlobalPage'))
const GapsPage = lazy(() => import('./pages/GapsPage'))
// The researchers' pages (P4), also on demand.
const SearchPage = lazy(() => import('./pages/SearchPage'))
const GalaxyPage = lazy(() => import('./pages/GalaxyPage'))
const KeywordsPage = lazy(() => import('./pages/KeywordsPage'))
const ReferencesPage = lazy(() => import('./pages/ReferencesPage'))

function Lazy({ children }: { children: ReactNode }) {
  return <Suspense fallback={<RouteLoading />}>{children}</Suspense>
}

export default function App() {
  return (
    <Routes>
      <Route path="/brief" element={<Lazy><BriefPage /></Lazy>} />
      <Route path="/embed/topic/:id" element={<Lazy><EmbedTopic /></Lazy>} />
      <Route path="/embed/emerging" element={<Lazy><EmbedEmerging /></Lazy>} />
      <Route path="/embed/*" element={<Lazy><EmbedTopic /></Lazy>} />
      <Route element={<Layout />}>
        <Route index element={<Navigate to="/overview" replace />} />
        <Route path="overview" element={<OverviewPage />} />
        <Route path="atlas" element={<Lazy><AtlasPage /></Lazy>} />
        <Route path="topics/:id" element={<TopicPage />} />
        <Route path="emerging" element={<EmergingPage />} />
        <Route path="journals" element={<Lazy><JournalsPage /></Lazy>} />
        <Route path="journals/:id" element={<Lazy><JournalPage /></Lazy>} />
        <Route path="methods" element={<Lazy><MethodsPage /></Lazy>} />
        <Route path="changes" element={<Lazy><ChangesPage /></Lazy>} />
        <Route path="match" element={<Lazy><MatchPage /></Lazy>} />
        <Route path="institutions" element={<Lazy><InstitutionsPage /></Lazy>} />
        <Route path="institutions/:id" element={<Lazy><InstitutionPage /></Lazy>} />
        <Route path="regions" element={<Lazy><RegionsPage /></Lazy>} />
        <Route path="sdg" element={<Lazy><SdgPage /></Lazy>} />
        <Route path="global" element={<Lazy><GlobalPage /></Lazy>} />
        <Route path="gaps" element={<Lazy><GapsPage /></Lazy>} />
        <Route path="search" element={<Lazy><SearchPage /></Lazy>} />
        <Route path="galaxy" element={<Lazy><GalaxyPage /></Lazy>} />
        <Route path="keywords" element={<Lazy><KeywordsPage /></Lazy>} />
        <Route path="references" element={<Lazy><ReferencesPage /></Lazy>} />
        <Route path="compare" element={<ComparePage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
