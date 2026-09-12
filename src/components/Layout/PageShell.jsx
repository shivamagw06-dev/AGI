import { Helmet } from 'react-helmet-async';
import { Link } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';

export default function PageShell({
  title,
  description,
  metaTitle,
  eyebrow,
  backTo = '/',
  backLabel = 'Back to Home',
  children,
  className = '',
  theme = 'light',
  wide = false,
}) {
  const isLight = theme === 'light';

  return (
    <div
      className={`min-h-screen ${isLight ? 'bg-white' : 'bg-slate-950'} ${className}`}
    >
      <Helmet>
        <title>{metaTitle || `${title} | Agarwal Global Investments`}</title>
        {description && <meta name="description" content={description} />}
      </Helmet>

      <div className={`border-b ${isLight ? 'border-slate-200 bg-white' : 'border-white/10 bg-slate-950'}`}>
        <div
          className={`${
            wide ? 'w-full max-w-none' : 'max-w-4xl mx-auto'
          } px-4 sm:px-6 lg:px-8 xl:px-10 2xl:px-12 ${wide ? 'py-8 lg:py-10' : 'py-12 lg:py-14'}`}
        >
          <Link
            to={backTo}
            className={`inline-flex items-center gap-2 text-sm mb-6 transition-colors ${
              isLight ? 'text-slate-500 hover:text-slate-900' : 'text-slate-400 hover:text-white'
            }`}
          >
            <ArrowLeft size={16} />
            {backLabel}
          </Link>
          {eyebrow && (
            <span
              className={`text-sm font-semibold uppercase tracking-widest ${
                isLight ? 'text-blue-700' : 'text-blue-400'
              }`}
            >
              {eyebrow}
            </span>
          )}
          <h1
            className={`mt-2 text-3xl md:text-4xl font-bold tracking-tight ${
              isLight ? 'text-slate-900' : 'text-white'
            }`}
          >
            {title}
          </h1>
          {description && (
            <p
              className={`mt-4 text-lg leading-relaxed ${
                wide ? 'max-w-5xl' : 'max-w-3xl'
              } ${isLight ? 'text-slate-600' : 'text-slate-300'}`}
            >
              {description}
            </p>
          )}
        </div>
      </div>

      <div
        className={`${
          wide ? 'w-full max-w-none' : 'max-w-4xl mx-auto'
        } px-4 sm:px-6 lg:px-8 xl:px-10 2xl:px-12 ${wide ? 'py-6 lg:py-8' : 'py-10 lg:py-14'}`}
      >
        {children}
      </div>
    </div>
  );
}

export function LegalSection({ title, children, theme = 'light' }) {
  const isLight = theme === 'light';
  return (
    <section className="mb-10">
      <h2 className={`text-xl font-semibold mb-3 ${isLight ? 'text-slate-900' : 'text-white'}`}>
        {title}
      </h2>
      <div
        className={`leading-relaxed space-y-3 text-[15px] ${
          isLight ? 'text-slate-700' : 'text-slate-300'
        }`}
      >
        {children}
      </div>
    </section>
  );
}
