import { NavLink } from 'react-router-dom';

export default function ManualScreenerTabs() {
  return <nav className="manual-screener-tabs" aria-label="Stock screens">
    <NavLink to="/agi/screeners" end>Low P/E</NavLink>
    <NavLink to="/agi/screeners/promoter-holdings">Promoter holdings rising</NavLink>
    <NavLink to="/agi/screeners/piotroski">High Piotroski Score</NavLink>
  </nav>;
}
