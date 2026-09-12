// src/pages/PublicProfile.jsx
import React, { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { getPublicProfileByHandle } from "../lib/profileApi";

/**
 * PublicProfile
 * Fetches a public user profile by handle and renders a LinkedIn-like public page.
 *
 * Expects getPublicProfileByHandle(handle) to return an object like:
 * {
 *   profile: { full_name, headline, location, industry, website, twitter, github, photo_url, banner_url, summary },
 *   experiences: [{ id, title, company, start_date, end_date, is_current, location, description }],
 *   educations: [{ id, school, degree, field, start_year, end_year, description }],
 *   certifications: [...],
 *   projects: [{ id, name, url, role, start_date, end_date, description }],
 *   skills: [ { skill_id, name, endorsement_count } | "Python" ]
 * }
 */

function formatDate(isoOrYear) {
  if (!isoOrYear) return "";
  // If it looks like a year (YYYY)
  if (/^\d{4}$/.test(String(isoOrYear))) return String(isoOrYear);
  try {
    const d = new Date(isoOrYear);
    if (Number.isNaN(d.getTime())) return String(isoOrYear);
    return d.toLocaleString(undefined, { month: "short", year: "numeric" }); // e.g. "Oct 2024"
  } catch {
    return String(isoOrYear);
  }
}

export default function PublicProfile() {
  const { handle } = useParams();
  const [data, setData] = useState(null);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    setLoading(true);
    setErr("");
    setData(null);

    (async () => {
      try {
        if (!handle) throw new Error("Invalid handle");
        const d = await getPublicProfileByHandle(handle);
        if (!mounted) return;
        if (!d || !d.profile) {
          setErr("Profile not found or not public.");
        } else {
          setData(d);
        }
      } catch (e) {
        console.error("PublicProfile error:", e);
        if (mounted) setErr("Profile not found or not public.");
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [handle]);

  if (loading) return <div className="p-6">Loading…</div>;
  if (err) return <div className="p-6 text-red-600">{err}</div>;
  if (!data) return <div className="p-6">No data available.</div>;

  const {
    profile = {},
    experiences = [],
    educations = [],
    certifications = [],
    projects = [],
    skills = [],
  } = data;

  const {
    full_name,
    headline,
    location,
    industry,
    website,
    github,
    twitter,
    photo_url,
    banner_url,
    summary,
  } = profile;

  // normalize skills: allow strings or objects
  const normalizedSkills = (skills || []).map((s) => {
    if (!s) return null;
    if (typeof s === "string") return { id: s, name: s, endorsement_count: 0 };
    // incoming object variations: { skill_id, name } or { skill_id, skill: { name } } etc.
    const id = s.skill_id ?? s.id ?? s.name ?? s.skill?.id ?? JSON.stringify(s);
    const name = s.name ?? s.skill?.name ?? s.skill_name ?? s;
    const endorsement_count = s.endorsement_count ?? s.endorsements ?? 0;
    return { id, name, endorsement_count };
  }).filter(Boolean);

  return (
    <div className="max-w-4xl mx-auto">
      <div className="relative">
        {banner_url ? (
          <img
            src={banner_url}
            alt={`${full_name ?? "User"} banner`}
            className="w-full h-56 object-cover rounded-md"
          />
        ) : (
          <div className="w-full h-56 bg-gray-100 rounded-md" />
        )}

        <div
          className="absolute left-6 -bottom-14 w-28 h-28 rounded-full border-4 border-white overflow-hidden bg-white"
          aria-hidden
        >
          {photo_url ? (
            <img
              src={photo_url}
              alt={`${full_name ?? "User"} avatar`}
              className="w-full h-full object-cover"
            />
          ) : (
            <div className="w-full h-full flex items-center justify-center text-xl text-slate-600 font-semibold">
              {(full_name || "U")
                .split(" ")
                .map((s) => s[0])
                .slice(0, 2)
                .join("")}
            </div>
          )}
        </div>
      </div>

      <div className="px-6 mt-16">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold">{full_name ?? "Unnamed"}</h1>
            {headline && <div className="text-lg opacity-80 mt-1">{headline}</div>}
            {(location || industry) && (
              <div className="text-sm opacity-70 mt-1">
                {[location, industry].filter(Boolean).join(" · ")}
              </div>
            )}

            <div className="mt-3 space-x-3">
              {website && (
                <a
                  className="underline"
                  href={website.startsWith("http") ? website : `https://${website}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Website
                </a>
              )}
              {github && (
                <a
                  className="underline"
                  href={github.startsWith("http") ? github : `https://github.com/${github}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  GitHub
                </a>
              )}
              {twitter && (
                <a
                  className="underline"
                  href={twitter.startsWith("http") ? twitter : `https://twitter.com/${twitter.replace(/^@/, "")}`}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Twitter
                </a>
              )}
            </div>
          </div>

          <div className="text-sm text-slate-500">
            {/* If you want a follow/contact CTA, put it here — using Link for internal routes */}
            <Link to={`/connect/${handle}`} className="px-3 py-2 border rounded-md inline-block">
              Connect
            </Link>
          </div>
        </div>

        {summary && <p className="mt-6 whitespace-pre-wrap text-slate-700">{summary}</p>}

        {/* Skills */}
        {normalizedSkills.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xl font-semibold mb-2">Skills</h2>
            <div className="flex flex-wrap gap-2">
              {normalizedSkills.map((s) => (
                <span key={s.id} className="px-3 py-1 border rounded text-sm flex items-center gap-2">
                  <span>{s.name}</span>
                  {s.endorsement_count ? <small className="text-xs opacity-60">· {s.endorsement_count}</small> : null}
                </span>
              ))}
            </div>
          </section>
        )}

        {/* Experience */}
        {Array.isArray(experiences) && experiences.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xl font-semibold mb-2">Experience</h2>
            <div className="space-y-3">
              {experiences.map((x) => {
                const start = formatDate(x.start_date ?? x.start_month ?? x.start_year);
                const end = x.is_current ? "Present" : formatDate(x.end_date ?? x.end_month ?? x.end_year);
                return (
                  <div key={x.id ?? `${x.company}-${x.title}-${start}`} className="border rounded p-3 bg-white">
                    <div className="font-semibold text-slate-800">{x.title ?? "Role"}</div>
                    <div className="text-sm opacity-80">{x.company}</div>
                    <div className="text-xs opacity-70 mb-2">
                      {[start, end].filter(Boolean).join(" – ")}
                      {x.location ? ` · ${x.location}` : ""}
                    </div>
                    {x.description && <div className="text-sm whitespace-pre-wrap text-slate-700">{x.description}</div>}
                  </div>
                );
              })}
            </div>
          </section>
        )}

        {/* Education */}
        {Array.isArray(educations) && educations.length > 0 && (
          <section className="mt-8">
            <h2 className="text-xl font-semibold mb-2">Education</h2>
            <div className="space-y-2">
              {educations.map((e) => (
                <div key={e.id ?? `${e.school}-${e.degree}`} className="border rounded p-3 bg-white">
                  <div className="font-semibold">{e.school}</div>
                  <div className="text-sm opacity-80">{[e.degree, e.field].filter(Boolean).join(" · ")}</div>
                  <div className="text-xs opacity-70 mb-2">{[e.start_year, e.end_year].filter(Boolean).join(" – ")}</div>
                  {e.description && <div className="text-sm whitespace-pre-wrap text-slate-700">{e.description}</div>}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Projects */}
        {Array.isArray(projects) && projects.length > 0 && (
          <section className="mt-8 mb-10">
            <h2 className="text-xl font-semibold mb-2">Projects</h2>
            <div className="space-y-2">
              {projects.map((p) => (
                <div key={p.id ?? p.name} className="border rounded p-3 bg-white">
                  <div className="font-semibold">
                    {p.url ? (
                      <a href={p.url} target="_blank" rel="noopener noreferrer" className="underline">
                        {p.name}
                      </a>
                    ) : (
                      p.name
                    )}
                  </div>
                  {p.role && <div className="text-sm opacity-80">{p.role}</div>}
                  <div className="text-xs opacity-70 mb-2">{[formatDate(p.start_date), formatDate(p.end_date)].filter(Boolean).join(" – ")}</div>
                  {p.description && <div className="text-sm whitespace-pre-wrap text-slate-700">{p.description}</div>}
                </div>
              ))}
            </div>
          </section>
        )}

        {/* Certifications (optional) */}
        {Array.isArray(certifications) && certifications.length > 0 && (
          <section className="mt-8 mb-10">
            <h2 className="text-xl font-semibold mb-2">Certifications</h2>
            <div className="space-y-2">
              {certifications.map((c) => (
                <div key={c.id ?? c.name} className="border rounded p-3 bg-white">
                  <div className="font-semibold">{c.name}</div>
                  {c.issuer && <div className="text-sm opacity-80">{c.issuer}</div>}
                  {c.date && <div className="text-xs opacity-70">{formatDate(c.date)}</div>}
                </div>
              ))}
            </div>
          </section>
        )}
      </div>
    </div>
  );
}
