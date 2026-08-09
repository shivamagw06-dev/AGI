// src/App.jsx
import React, { useEffect, Suspense } from 'react';
import { Helmet, HelmetProvider } from 'react-helmet-async';
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import Header from "@/components/Layout/Header";
import { MarketDataProvider } from "@/contexts/MarketDataContext";
import Footer from '@/components/Footer';
import { Toaster } from '@/components/ui/toaster';
import PinGate from '@/components/auth/PinGate';

const AdminRoutes = React.lazy(() => import('@/pages/admin/AdminRoutes'));
const CategoryPage = React.lazy(() => import('@/pages/CategoryPage'));
const ArticlesFeed = React.lazy(() => import('@/components/ArticlesFeed'));
const About = React.lazy(() => import('@/components/About'));
const Contact = React.lazy(() => import('@/components/Contact'));
const ResearchNotes = React.lazy(() => import('@/components/ResearchNotes'));
const DealTracker = React.lazy(() => import('@/components/DealTracker'));
const ProfileEditor = React.lazy(() => import('@/pages/ProfileEditor'));
const PublicProfile = React.lazy(() => import('@/pages/PublicProfile'));
const LoginPage = React.lazy(() => import('@/components/LoginPage'));
const ArticlePage = React.lazy(() => import('@/components/ArticlePage'));
const NotFound = React.lazy(() => import('@/components/NotFound'));
const Business = React.lazy(() => import('@/components/Business.jsx'));
const MarketUpdates = React.lazy(() => import('@/pages/MarketUpdates'));
const SectionArticlesPage = React.lazy(() => import('@/pages/SectionArticlesPage'));
const Events = React.lazy(() => import('@/pages/Events'));
const PrivacyPolicy = React.lazy(() => import('@/pages/legal/PrivacyPolicy'));
const TermsOfService = React.lazy(() => import('@/pages/legal/TermsOfService'));
const Disclaimer = React.lazy(() => import('@/pages/legal/Disclaimer'));
const SebiDisclosure = React.lazy(() => import('@/pages/legal/SebiDisclosure'));
const VerifyEmailPage = React.lazy(() => import('@/pages/auth/VerifyEmailPage'));
const ForgotPasswordPage = React.lazy(() => import('@/pages/auth/ForgotPasswordPage'));
const ResetPasswordPage = React.lazy(() => import('@/pages/auth/ResetPasswordPage'));
const PinUnlockPage = React.lazy(() => import('@/pages/auth/PinUnlockPage'));
const AccountSecurityPage = React.lazy(() => import('@/pages/auth/AccountSecurityPage'));
const Opinions = React.lazy(() => import('@/components/Opinions'));
const Markets = React.lazy(() => import('@/pages/Markets'));
const MarketIntelligence = React.lazy(() => import('@/pages/MarketIntelligence'));
const MarketSectorIntelligence = React.lazy(() => import('@/pages/MarketSectorIntelligence'));
const GlobalMarketsPage = React.lazy(() => import('@/pages/GlobalMarketsPage'));
const PreMarketIntelligence = React.lazy(() => import('@/pages/PreMarketIntelligence'));
const Nifty500StockResearch = React.lazy(() => import('@/pages/Nifty500StockResearch'));
const IpoDetailPage = React.lazy(() => import('@/pages/IpoDetailPage'));
const IpoIntelligencePage = React.lazy(() => import('@/pages/IpoIntelligencePage'));
const MarketDataCentre = React.lazy(() => import('@/pages/MarketDataCentre'));
const DataHealthSheet = React.lazy(() => import('@/pages/DataHealthSheet'));
const PortfolioDesk = React.lazy(() => import('@/pages/PortfolioDesk'));
const ThemeDesk = React.lazy(() => import('@/pages/ThemeDesk'));
const SectorDesk = React.lazy(() => import('@/pages/SectorDesk'));
const ResearchWorkflowDesk = React.lazy(() => import('@/pages/ResearchWorkflowDesk'));
const AskAgiPage = React.lazy(() => import('@/pages/AskAgiPage'));
const ValuationIntelligence = React.lazy(() => import('@/pages/admin/ValuationIntelligence'));
const ValuationTerminal = React.lazy(() => import('@/pages/admin/ValuationTerminal'));
const AgiRoutes = React.lazy(() => import('@/pages/agi/AgiRoutes'));
const PredictionCentre = React.lazy(() => import('@/pages/PredictionCentre'));
const PersonalWorkspace = React.lazy(() => import('@/pages/PersonalWorkspace'));
const ResearchTerminalHome = React.lazy(() => import('@/components/Home/ResearchTerminalHome'));
const HedgeFundPage = React.lazy(() => import('@/pages/HedgeFundPage'));
const HedgeFundSignalPage = React.lazy(() => import('@/pages/HedgeFundSignalPage'));
const LiveAlphaPage = React.lazy(() => import('@/pages/LiveAlphaPage'));
const PrivateEquityPage = React.lazy(() => import('@/pages/PrivateEquityPage'));
const PrivateEquityFirmPage = React.lazy(() => import('@/pages/PrivateEquityFirmPage'));
const IntelligenceEntityPage = React.lazy(() => import('@/pages/IntelligenceEntityPage'));
const EconomicsPage = React.lazy(() => import('@/pages/EconomicsPage'));

function RouteFallback({ label = 'Loading…' }) {
  return <div className="min-h-[40vh] p-8 text-center text-slate-600">{label}</div>;
}

function HomeLayout() {
  // Public research-terminal homepage — admin shells stay under /admin/*.
  return <ResearchTerminalHome />;
}

function AppShell() {
  const location = useLocation();
  const isAdmin = location.pathname.startsWith('/admin');
  const isAskWorkspace = location.pathname === '/ask';
  const isValuationIntelligence =
    location.pathname === '/valuation-intelligence' || location.pathname === '/valuation-terminal';
  const isAgiProduct = location.pathname === '/agi' || location.pathname.startsWith('/agi/');

  useEffect(() => {
    if (!isAdmin && !isAskWorkspace) {
      document.documentElement.classList.remove('dark');
    }
  }, [isAdmin, isAskWorkspace, location.pathname]);

  if (isAdmin) {
    return (
      <Suspense fallback={<div className="min-h-screen bg-[#0b0e14] p-8 text-center text-slate-400">Loading admin…</div>}>
        <Routes>
          <Route path="/admin/*" element={<AdminRoutes />} />
        </Routes>
      </Suspense>
    );
  }

  // Phase 2 AGI product shell — full-bleed institutional workflow (no public chrome).
  if (isAgiProduct) {
    return (
      <MarketDataProvider>
        <PinGate>
          <Suspense fallback={<div className="min-h-screen bg-[#f6f7f9] p-8 text-center text-slate-600">Loading AGI…</div>}>
            <Routes>
              <Route path="/agi/*" element={<AgiRoutes />} />
            </Routes>
          </Suspense>
          <Toaster />
        </PinGate>
      </MarketDataProvider>
    );
  }

  // Ask AGI is a full-bleed institutional research workspace — no public chrome.
  if (isAskWorkspace) {
    return (
      <MarketDataProvider>
        <PinGate>
          <Suspense fallback={<div className="min-h-screen bg-[#0b0e14] p-8 text-center text-slate-300">Loading Ask AGI…</div>}>
            <Routes>
              <Route path="/ask" element={<AskAgiPage />} />
            </Routes>
          </Suspense>
          <Toaster />
        </PinGate>
      </MarketDataProvider>
    );
  }

  // Valuation Intelligence — full-bleed institutional consensus (read for users; admin import on /admin).
  if (isValuationIntelligence) {
    return (
      <MarketDataProvider>
        <PinGate>
          <Suspense fallback={<div className="min-h-screen bg-[#eef3f8] p-8 text-center text-slate-600">Loading Valuation Intelligence…</div>}>
            <Routes>
              <Route path="/valuation-intelligence" element={<ValuationIntelligence />} />
              <Route path="/valuation-terminal" element={<ValuationTerminal />} />
            </Routes>
          </Suspense>
          <Toaster />
        </PinGate>
      </MarketDataProvider>
    );
  }

  return (
    <>
      <MarketDataProvider enabled={location.pathname !== '/'}>
        <PinGate>
          <Header />
          <main>
            <Suspense fallback={<RouteFallback />}>
              <PublicRoutes />
            </Suspense>
          </main>
          <Footer />
          <Toaster />
        </PinGate>
      </MarketDataProvider>
    </>
  );
}

function PublicRoutes() {
  return (
    <Routes>
      <Route path="/" element={<HomeLayout />} />
      <Route path="/ask" element={<AskAgiPage />} />
      <Route path="/predictions" element={<PredictionCentre />} />
      <Route path="/workspace" element={<PersonalWorkspace />} />

      <Route path="/market-updates" element={<MarketUpdates />} />
      <Route path="/updates/:sectionId" element={<SectionArticlesPage />} />
      <Route path="/company-updates" element={<SectionArticlesPage overrideId="company-updates" />} />

      <Route path="/research" element={<ArticlesFeed variant="light" />} />
      <Route path="/sections/live-articles" element={<Navigate replace to="/research" />} />
      <Route path="/live-articles" element={<Navigate replace to="/research" />} />

      <Route path="/category/:slug" element={<CategoryPage />} />

      <Route path="/markets" element={<Markets />} />
      <Route path="/sections/markets" element={<Navigate replace to="/markets" />} />
      <Route path="/market-intelligence" element={<MarketIntelligence />} />
      <Route path="/market-sector-intelligence" element={<MarketSectorIntelligence />} />
      <Route path="/macro-intelligence" element={<Navigate replace to="/global-markets" />} />
      <Route path="/hedge-fund" element={<HedgeFundPage />} />
      <Route path="/live-alpha" element={<LiveAlphaPage />} />
      <Route path="/hedge-fund/alpha-opportunities" element={<HedgeFundSignalPage kind="alpha" />} />
      <Route path="/hedge-fund/technical-analysis" element={<Navigate replace to="/hedge-fund/alpha-opportunities" />} />
      <Route path="/hedge-fund/strategy-lab" element={<Navigate replace to="/hedge-fund" />} />
      <Route path="/private-markets" element={<PrivateEquityPage />} />
      <Route path="/private-markets/firms/:slug" element={<PrivateEquityFirmPage />} />
      <Route path="/private-markets/entities/:slug" element={<IntelligenceEntityPage />} />
      <Route path="/private-equity" element={<Navigate replace to="/private-markets" />} />
      <Route path="/private-equity/firms/:slug" element={<PrivateEquityFirmPage />} />
      <Route path="/global-markets" element={<GlobalMarketsPage />} />
      <Route path="/economics" element={<EconomicsPage />} />
      <Route path="/global" element={<Navigate replace to="/global-markets" />} />
      <Route path="/global-intelligence" element={<Navigate replace to="/global-markets" />} />
      <Route path="/economy" element={<Navigate replace to="/economics" />} />
      <Route path="/pre-market" element={<PreMarketIntelligence />} />
      <Route path="/updates/pre-market" element={<Navigate replace to="/pre-market" />} />
      <Route path="/market-data" element={<MarketDataCentre />} />
      <Route path="/data-health" element={<DataHealthSheet />} />
      <Route path="/research/stocks/:symbol" element={<Nifty500StockResearch />} />
      <Route path="/portfolio" element={<PortfolioDesk />} />
      <Route path="/themes/:themeId" element={<ThemeDesk />} />
      <Route path="/themes" element={<Navigate replace to="/themes/credit_growth" />} />
      <Route path="/sectors/:sectorId" element={<SectorDesk />} />
      <Route path="/research/workflow" element={<ResearchWorkflowDesk />} />
      <Route path="/ipo-intelligence" element={<IpoIntelligencePage />} />
      <Route path="/ipos" element={<Navigate replace to="/ipo-intelligence" />} />
      <Route path="/ipos/:symbol" element={<IpoDetailPage />} />

      {/* Legacy redirects */}
      <Route path="/companies" element={<Navigate replace to="/company-updates" />} />
      <Route path="/insights" element={<Navigate replace to="/sections/opinions-editorials" />} />

      <Route path="/sections/research-notes" element={<ResearchNotes />} />
      <Route path="/research-notes" element={<Navigate replace to="/sections/research-notes" />} />

      <Route path="/sections/deal-tracker" element={<DealTracker />} />
      <Route path="/deal-tracker" element={<Navigate replace to="/sections/deal-tracker" />} />

      <Route path="/sections/opinions-editorials" element={<Opinions />} />
      <Route path="/opinions-editorials" element={<Navigate replace to="/sections/opinions-editorials" />} />

      <Route path="/business" element={<Business />} />

      <Route path="/events" element={<Events />} />
      <Route path="/events-webinars" element={<Navigate replace to="/events" />} />

      <Route path="/privacy" element={<PrivacyPolicy />} />
      <Route path="/terms" element={<TermsOfService />} />
      <Route path="/disclaimer" element={<Disclaimer />} />
      <Route path="/sebi-disclosure" element={<SebiDisclosure />} />

      <Route path="/login" element={<LoginPage />} />
      <Route path="/verify-email" element={<VerifyEmailPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/unlock-pin" element={<PinUnlockPage />} />
      <Route path="/account/security" element={<AccountSecurityPage />} />
      <Route path="/article/:slug" element={<ArticlePage />} />
      <Route path="/articles/new" element={<Navigate replace to="/admin/articles/new" />} />
      <Route path="/write" element={<Navigate replace to="/admin/articles/new" />} />
      <Route
        path="/knowledge-operations"
        element={<Navigate replace to="/admin/knowledge-operations" />}
      />
      <Route
        path="/investment-office"
        element={<Navigate replace to="/admin/investment-office" />}
      />

      <Route path="/about" element={<About />} />
      <Route path="/contact" element={<Contact />} />

      <Route path="/profile/edit" element={<ProfileEditor />} />
      <Route path="/u/:handle" element={<PublicProfile />} />

      <Route path="/404" element={<NotFound />} />
      <Route path="*" element={<Navigate replace to="/404" />} />
    </Routes>
  );
}

function App() {
  useEffect(() => {
    try {
      const apiUrl = import.meta.env.VITE_API_URL || null;
      if (apiUrl) {
        window.API_URL = apiUrl;
      }
    } catch {
      /* ignore */
    }
  }, []);

  return (
    <HelmetProvider>
      <BrowserRouter>
        <div className="min-h-screen bg-white">
          <Helmet>
            <title>AGI — Independent Equity Research for Indian Investors</title>
            <meta
              name="description"
              content="Institutional-quality market research updated every trading day. Morning briefs, sector analysis, and company updates from Agarwal Global Investments."
            />
            <link rel="preconnect" href="https://fonts.googleapis.com" />
            <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
            <link
              href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Source+Serif+4:opsz,wght@8..60,500;8..60,600;8..60,700&display=swap"
              rel="stylesheet"
            />
          </Helmet>
          <AppShell />
        </div>
      </BrowserRouter>
    </HelmetProvider>
  );
}

export default App;
