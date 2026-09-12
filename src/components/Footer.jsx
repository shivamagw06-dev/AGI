import { Link } from 'react-router-dom';
import Logo from '@/components/Layout/Logo';

const LINKS = [
  { label: 'Research', to: '/research' },
  { label: 'Markets', to: '/market-intelligence' },
  { label: 'About', to: '/about' },
  { label: 'Newsletter', to: '/#newsletter' },
  { label: 'Privacy', to: '/privacy' },
  { label: 'Terms', to: '/terms' },
  { label: 'Contact', to: '/contact' },
  {
    label: 'LinkedIn',
    to: 'https://www.linkedin.com/company/agarwal-global-investments',
    external: true,
  },
];

export default function Footer() {
  return (
    <footer className="border-t border-[#e6e8ec] bg-white text-[#111111]">
      <div className="mx-auto max-w-[1680px] px-4 sm:px-6 lg:px-8 py-12">
        <div className="flex flex-col gap-8 md:flex-row md:items-start md:justify-between">
          <div>
            <Logo compact className="mb-3" />
            <p className="mt-3 max-w-sm text-xs leading-relaxed text-[#555555]">
              AGI is an AI-powered institutional research platform. Informational only — not investment advice.
            </p>
          </div>

          <nav aria-label="Footer" className="flex flex-wrap gap-x-5 gap-y-3">
            {LINKS.map((link) =>
              link.external ? (
                <a
                  key={link.label}
                  href={link.to}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-[#333333] hover:text-[#111111] hover:underline underline-offset-4"
                >
                  {link.label}
                </a>
              ) : (
                <Link
                  key={link.label}
                  to={link.to}
                  className="text-sm text-[#333333] hover:text-[#111111] hover:underline underline-offset-4"
                >
                  {link.label}
                </Link>
              )
            )}
          </nav>
        </div>

        <p className="mt-10 border-t border-[#eef0f3] pt-5 text-[11px] text-[#767676]">
          © {new Date().getFullYear()} Agarwal Global Investments. All rights reserved.
        </p>
      </div>
    </footer>
  );
}
