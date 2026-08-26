import { Route, Routes } from 'react-router-dom';
import RequireAskAgiAdmin from '@/components/auth/AskAgiAdminAccess';
import AgiLayout from './AgiLayout';
import DashboardPage from './DashboardPage';
import AskAgiProductPage from './AskAgiProductPage';
import CompaniesIndexPage from './CompaniesIndexPage';
import CompanyWorkspacePage from './CompanyWorkspacePage';
import PortfolioWorkspacePage from './PortfolioWorkspacePage';
import CommitteePage from './CommitteePage';
import MarketsWorkspacePage from './MarketsWorkspacePage';
import ResearchWorkspacePage from './ResearchWorkspacePage';
import WatchlistsWorkspacePage from './WatchlistsWorkspacePage';
import ComingSoonPage from './ComingSoonPage';
import SettingsPage from './SettingsPage';

export default function AgiRoutes() {
  return (
    <Routes>
      <Route element={<AgiLayout />}>
        <Route index element={<DashboardPage />} />
        <Route path="ask" element={<RequireAskAgiAdmin><AskAgiProductPage /></RequireAskAgiAdmin>} />
        <Route path="companies" element={<CompaniesIndexPage />} />
        <Route path="companies/:ticker" element={<CompanyWorkspacePage />} />
        <Route path="portfolio" element={<PortfolioWorkspacePage />} />
        <Route path="committee" element={<CommitteePage />} />
        <Route path="markets" element={<MarketsWorkspacePage />} />
        <Route path="research" element={<ResearchWorkspacePage />} />
        <Route path="watchlists" element={<WatchlistsWorkspacePage />} />
        <Route path="screeners" element={<ComingSoonPage area="screeners" />} />
        <Route path="notebook" element={<ComingSoonPage area="notebook" />} />
        <Route path="alerts" element={<ComingSoonPage area="alerts" />} />
        <Route path="settings" element={<SettingsPage />} />
      </Route>
    </Routes>
  );
}
