import { Navigate, Route, Routes } from 'react-router'
import { Layout } from './components/Layout'
import AboutPage from './pages/AboutPage'
import AtlasPage from './pages/AtlasPage'
import BriefPage from './pages/BriefPage'
import ComparePage from './pages/ComparePage'
import DataPage from './pages/DataPage'
import EmergingPage from './pages/EmergingPage'
import NotFoundPage from './pages/NotFoundPage'
import OverviewPage from './pages/OverviewPage'
import TopicPage from './pages/TopicPage'

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
        <Route path="compare" element={<ComparePage />} />
        <Route path="data" element={<DataPage />} />
        <Route path="about" element={<AboutPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>
    </Routes>
  )
}
