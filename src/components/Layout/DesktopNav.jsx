import { NavLink } from "react-router-dom";

const navItems = [
  { title: "Research", href: "/sections/live-articles" },
  { title: "Markets", href: "/markets/stocks" },
  { title: "Economy", href: "/economy" },
  { title: "Companies", href: "/companies" },
  { title: "Hedge Funds", href: "/institutional-holdings" },
  { title: "Business", href: "/business" },
  { title: "Insights", href: "/sections/research-notes" },
  { title: "About", href: "/about" },
];

export default function DesktopNav() {
  return (
    <nav className="hidden lg:flex items-center gap-8">
      {navItems.map((item) => (
        <NavLink
          key={item.title}
          to={item.href}
          className={({ isActive }) =>
            `text-[15px] font-medium transition-colors ${
              isActive
                ? "text-slate-900"
                : "text-slate-600 hover:text-blue-700"
            }`
          }
        >
          {item.title}
        </NavLink>
      ))}
    </nav>
  );
}