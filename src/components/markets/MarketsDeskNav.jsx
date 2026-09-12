import { NavLink } from 'react-router-dom';

const LINKS = [
  { to: '/markets/stocks', label: 'Stocks', end: false },
  { to: '/markets', label: 'Analysis', end: true },
];

export default function MarketsDeskNav() {
  return (
    <nav className="mt-6 flex border-t border-[#dddddd]" aria-label="Markets sections">
      {LINKS.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          end={link.end}
          className={({ isActive }) =>
            `relative mr-6 py-3.5 pr-4 text-[13px] font-bold ${
              isActive
                ? 'text-[#111111] after:absolute after:left-0 after:right-4 after:-bottom-px after:h-0.5 after:bg-[#ff6600]'
                : 'text-[#767676] hover:text-[#111111]'
            }`
          }
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
