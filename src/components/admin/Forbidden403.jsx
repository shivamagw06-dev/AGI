import { Link } from 'react-router-dom';
import { ShieldOff } from 'lucide-react';

/** HTTP-style 403 for admin-only Knowledge Operations direct URL access. */
export default function Forbidden403({ resource = 'Knowledge Operations' }) {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[#f7f7f5] px-6 text-[#111]">
      <div className="max-w-md text-center">
        <ShieldOff className="mx-auto h-10 w-10 text-[#b42318]" />
        <p className="mt-4 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#767676]">
          403 Forbidden
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight">Access denied</h1>
        <p className="mt-3 text-sm leading-relaxed text-[#555]">
          {resource} is restricted to authenticated AGI administrators. Regular users cannot view
          this control room.
        </p>
        <Link
          to="/"
          className="mt-6 inline-block border border-[#111] px-4 py-2 text-sm font-medium hover:bg-[#111] hover:text-white"
        >
          Return home
        </Link>
      </div>
    </div>
  );
}
