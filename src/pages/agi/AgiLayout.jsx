import { useEffect, useState } from 'react';
import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';
import { NAV_ITEMS } from './helpers';
import './agi.css';

function titleForPath(pathname) {
  if (pathname === '/agi' || pathname === '/agi/') return 'Dashboard';
  if (pathname.startsWith('/agi/ask')) return 'Ask AGI';
  if (pathname.startsWith('/agi/companies')) return 'Companies';
  const hit = NAV_ITEMS.find((n) => n.to !== '/agi' && pathname.startsWith(n.to));
  return hit?.label || 'AGI';
}

export default function AgiLayout() {
  const location = useLocation();
  const [navOpen, setNavOpen] = useState(false);
  const pageTitle = titleForPath(location.pathname);
  const isAsk = location.pathname.startsWith('/agi/ask');

  useEffect(() => {
    setNavOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    document.documentElement.classList.remove('dark');
  }, []);

  return (
    <div className={`agi-app${navOpen ? ' agi-nav-open' : ''}`}>
      <Helmet>
        <title>{pageTitle} | AGI</title>
        <meta
          name="description"
          content="AGI institutional research platform — companies, portfolios, markets, and Ask AGI in one continuous workflow."
        />
      </Helmet>

      <div className="agi-overlay" onClick={() => setNavOpen(false)} aria-hidden="true" />

      <aside className="agi-nav" aria-label="AGI product navigation">
        <div className="agi-brand">
          <Link to="/agi">
            <div className="agi-brand-mark">AGI</div>
            <div className="agi-brand-sub">Institutional platform</div>
          </Link>
        </div>
        <ul className="agi-nav-list">
          {NAV_ITEMS.map((item) => (
            <li key={item.to}>
              <NavLink
                to={item.to}
                end={Boolean(item.end)}
                className={({ isActive }) => (isActive ? 'active' : undefined)}
              >
                {item.label}
              </NavLink>
            </li>
          ))}
        </ul>
        <div className="agi-nav-footer">
          Companies · Portfolios · Research · Markets · Ideas
        </div>
      </aside>

      <div className="agi-main">
        <header className="agi-topbar">
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <button
              type="button"
              className="agi-menu-btn"
              aria-label="Open navigation"
              onClick={() => setNavOpen(true)}
            >
              ☰
            </button>
            <div className="agi-topbar-title">{pageTitle}</div>
          </div>
          <div className="agi-topbar-actions">
            {!isAsk && (
              <Link className="agi-btn agi-btn-primary" to="/agi/ask">
                Ask AGI
              </Link>
            )}
            <Link className="agi-btn" to="/">
              Public site
            </Link>
          </div>
        </header>
        <div className={`agi-content${isAsk ? ' agi-content-ask' : ''}`}>
          <Outlet />
        </div>
      </div>
    </div>
  );
}
