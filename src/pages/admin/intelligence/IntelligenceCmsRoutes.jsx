import { lazy, Suspense } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import IntelligenceCmsLayout from './IntelligenceCmsLayout';

const IntelligenceDashboard = lazy(() => import('./IntelligenceDashboard'));
const IntelligenceModulePage = lazy(() => import('./IntelligenceModulePage'));
const IntelligenceEntitiesAdmin = lazy(() => import('./IntelligenceEntitiesAdmin'));
const PrivateMarketsDataAdmin = lazy(() => import('./PrivateMarketsDataAdmin'));
const InsiderTradingDataAdmin = lazy(() => import('./InsiderTradingDataAdmin'));

export default function IntelligenceCmsRoutes() {
  return (
    <Suspense fallback={<div className="p-6 text-sm text-slate-500">Loading intelligence workspace...</div>}>
      <Routes>
        <Route element={<IntelligenceCmsLayout />}>
          <Route index element={<IntelligenceDashboard />} />
          <Route path="entities" element={<IntelligenceEntitiesAdmin />} />
          <Route path="private-markets-data" element={<PrivateMarketsDataAdmin />} />
          <Route path="insider-trading-data" element={<InsiderTradingDataAdmin />} />
          <Route path="valuation-monitor" element={<IntelligenceModulePage />} />
          <Route path=":moduleSlug" element={<IntelligenceModulePage />} />
          <Route path="*" element={<Navigate to="/admin/intelligence" replace />} />
        </Route>
      </Routes>
    </Suspense>
  );
}
