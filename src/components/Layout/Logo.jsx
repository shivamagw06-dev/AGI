import { Link } from 'react-router-dom';

// Root copy is required for Hostinger Git sync (public/ is not served at /).
const LOGO_SRC = '/agi-logo.png';

export default function Logo({ compact = false, className = '' }) {
  return (
    <Link
      to="/"
      className={`group inline-flex items-center gap-2.5 hover:opacity-90 transition-opacity ${className}`}
      aria-label="Agarwal Global Investments — Home"
    >
      <img
        src={LOGO_SRC}
        alt="Agarwal Global Investments"
        width={compact ? 40 : 48}
        height={compact ? 35 : 42}
        className={`${compact ? 'h-9 w-auto' : 'h-11 w-auto'} object-contain`}
        decoding="async"
      />
      {!compact && (
        <span className="hidden sm:flex flex-col leading-none">
          <span className="text-[10px] font-semibold tracking-[0.12em] uppercase text-[#333333]">
            Agarwal Global Investments
          </span>
          <span className="text-[9px] tracking-wide text-[#767676] mt-0.5">
            Independent Equity Research
          </span>
        </span>
      )}
    </Link>
  );
}
