import { Link, useLocation } from 'react-router-dom';
import { Helmet } from 'react-helmet-async';

const NAV = [
  { label: 'Home', to: '/' },
  { label: 'PE Intelligence', to: '/private-equity' },
  { label: 'Deal Tracker', to: '/sections/deal-tracker' },
  { label: 'Ask AGI', to: '/ask' },
];

export default function PeTerminalLayout({ title, children }) {
  const { pathname } = useLocation();

  return (
    <div className="pe-terminal">
      <Helmet>
        <title>{title ? `${title} | PE Intelligence | AGI` : 'Private Equity Intelligence | AGI'}</title>
      </Helmet>
      <header className="pe-nav">
        <div className="pe-nav-inner">
          <Link to="/" className="pe-title text-lg text-white no-underline">
            AGI <span className="pe-gold">PE</span>
          </Link>
          <nav className="pe-nav-links">
            {NAV.map((item) => (
              <Link
                key={item.to}
                to={item.to}
                className={pathname === item.to ? 'active' : ''}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
