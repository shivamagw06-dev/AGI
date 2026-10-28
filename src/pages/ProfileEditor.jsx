import React, { useState } from 'react';
import ProfileEditor from './ProfileEditor';

// LinkedIn-like Auth + Profile single-file React component (rewritten to use existing ProfileEditor.jsx)
// Tailwind CSS required in the project. Replace onAuthenticate handlers with real auth/profile APIs.

export function AuthCard({ onAuthenticate }) {
  const [mode, setMode] = useState('login'); // 'login' | 'signup'
  const [form, setForm] = useState({
    email: '',
    password: '',
    name: '',
    headline: '',
  });
  const [error, setError] = useState('');

  function update(e) {
    setForm(prev => ({ ...prev, [e.target.name]: e.target.value }));
  }

  function submit(e) {
    e.preventDefault();
    setError('');
    if (!form.email || !form.password) return setError('Please fill email & password.');
    if (mode === 'signup' && !form.name) return setError('Please enter your full name.');

    const profile = {
      name: mode === 'signup' ? form.name : 'Shivam Agarwal',
      headline: form.headline || 'Finance & Markets Analyst',
      email: form.email,
      avatarUrl: null,
      location: 'Mumbai, India',
      about: 'I write about markets, macro and investment strategy.',
      skills: ['Equity Research', 'Financial Modelling'],
      experiences: [
        { id: 1, title: 'Private Equity', company: '-', period: '2024 - 2025' },
      ],
      education: [
        { id: 1, degree: 'MBA Finance', school: 'Top Business School', period: '2022 - 2025' }
      ]
    };

    onAuthenticate(profile);
  }

  return (
    <div className="max-w-3xl mx-auto grid grid-cols-1 md:grid-cols-2 gap-8 bg-white shadow-2xl rounded-2xl overflow-hidden">
      <div className="hidden md:flex flex-col justify-center p-8 bg-gradient-to-b from-slate-50 to-white">
        <h2 className="text-3xl font-extrabold text-slate-800">Welcome to Agarwal Global</h2>
        <p className="mt-3 text-slate-500">Professional network focused on finance, markets and research. Create your profile, follow experts and discover insights.</p>
        <ul className="mt-6 space-y-3 text-sm text-slate-600">
          <li>• Share and publish research notes</li>
          <li>• Build your professional profile</li>
          <li>• Follow sectors & receive tailored updates</li>
        </ul>
      </div>

      <div className="p-8">
        <div className="flex items-center justify-between">
          <h3 className="text-xl font-semibold text-slate-800">{mode === 'login' ? 'Sign in' : 'Create an account'}</h3>
          <div className="text-sm text-slate-500">{mode === 'login' ? 'New here?' : 'Already have an account?'}
            <button onClick={() => setMode(mode === 'login' ? 'signup' : 'login')} className="ml-2 text-amber-600 font-medium">{mode === 'login' ? 'Create account' : 'Sign in'}</button>
          </div>
        </div>

        <form onSubmit={submit} className="mt-6 space-y-4">
          {mode === 'signup' && (
            <div>
              <label className="block text-sm text-slate-600">Full name</label>
              <input name="name" value={form.name} onChange={update} className="mt-2 w-full rounded-md border px-3 py-2 text-sm shadow-sm" placeholder="Your full name" />
            </div>
          )}

          <div>
            <label className="block text-sm text-slate-600">Email</label>
            <input name="email" type="email" value={form.email} onChange={update} className="mt-2 w-full rounded-md border px-3 py-2 text-sm shadow-sm" placeholder="name@company.com" />
          </div>

          <div>
            <label className="block text-sm text-slate-600">Password</label>
            <input name="password" type="password" value={form.password} onChange={update} className="mt-2 w-full rounded-md border px-3 py-2 text-sm shadow-sm" placeholder="Minimum 8 characters" />
          </div>

          <div>
            <label className="block text-sm text-slate-600">Headline (optional)</label>
            <input name="headline" value={form.headline} onChange={update} className="mt-2 w-full rounded-md border px-3 py-2 text-sm shadow-sm" placeholder="e.g. Equity Research Analyst | MBA" />
          </div>

          {error && <div className="text-sm text-red-600">{error}</div>}

          <div className="flex flex-col sm:flex-row gap-3 mt-4">
            <button type="submit" className="flex-1 bg-amber-500 hover:bg-amber-600 text-white rounded-md py-2 font-medium">{mode === 'login' ? 'Sign in' : 'Create account'}</button>
            <button type="button" onClick={() => onAuthenticate(null)} className="flex-1 border rounded-md py-2 font-medium">Continue as guest</button>
          </div>

          <div className="pt-3">
            <div className="text-xs text-center text-slate-500">or continue with</div>
            <div className="mt-3 flex gap-3 justify-center">
              <button type="button" className="px-4 py-2 border rounded-md inline-flex items-center gap-2"> 
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M4 4h16v16H4z" stroke="#0A66C2" strokeWidth="1.2" strokeLinecap="round" strokeLinejoin="round"/></svg>
                LinkedIn
              </button>
              <button type="button" className="px-4 py-2 border rounded-md inline-flex items-center gap-2">Google</button>
            </div>
          </div>

          <p className="text-xs text-slate-400">By continuing, you agree to our Terms & Privacy Policy.</p>
        </form>
      </div>
    </div>
  );
}

export function ProfilePage({ profile: initialProfile, onSignOut }) {
  const [editing, setEditing] = useState(false);
  const [profile, setProfile] = useState(initialProfile || {
    name: 'Shivam Agarwal',
    headline: 'Finance & Markets Analyst',
    location: 'Mumbai, India',
    about: 'I write about markets, macro and investment strategy.',
    avatarUrl: null,
    skills: ['Equity Research', 'Financial Modelling', 'Econometrics'],
    experiences: [
      { id: 1, title: 'Risk Consultant', company: 'EY', period: '2024 - 2025', desc: 'Risk assessment, ESG reporting and internal audit projects.' },
    ],
    education: [
      { id: 1, degree: 'MBA Finance', school: 'Top Business School', period: '2022 - 2025' }
    ]
  });

  function saveProfile() {
    // TODO: call API to persist profile data
    setEditing(false);
  }

  return (
    <div className="max-w-5xl mx-auto bg-white rounded-2xl shadow-md p-6">
      <div className="flex items-start gap-6">
        <div className="w-28 h-28 rounded-full bg-slate-100 flex items-center justify-center overflow-hidden"> 
          {profile.avatarUrl ? <img src={profile.avatarUrl} alt="avatar" className="w-full h-full object-cover" /> : (
            <div className="text-slate-600 text-xl font-semibold">{(profile.name || 'U').split(' ').map(s=>s[0]).slice(0,2).join('')}</div>
          )}
        </div>

        <div className="flex-1">
          <div className="flex items-start justify-between">
            <div>
              <div className="text-2xl font-bold">{profile.name}</div>
              <div className="text-sm text-slate-500 mt-1">{profile.headline} • {profile.location}</div>
              <div className="mt-3 text-sm text-slate-700">{profile.about}</div>
              <div className="mt-4 flex flex-wrap gap-2">
                {profile.skills.map(s => (
                  <span key={s} className="text-xs px-3 py-1 border rounded-full">{s}</span>
                ))}
              </div>
            </div>

            <div className="flex flex-col items-end gap-2">
              <div className="text-sm text-slate-500">Profile strength: <span className="font-medium text-amber-600">80%</span></div>
              <div className="flex gap-2">
                <button onClick={() => setEditing(e => !e)} className="px-4 py-2 border rounded-md">{editing ? 'Close editor' : 'Edit profile'}</button>
                <button onClick={onSignOut} className="px-4 py-2 bg-red-100 text-red-700 rounded-md">Sign out</button>
              </div>
            </div>
          </div>

          <div className="mt-6">
            <h4 className="text-lg font-semibold">Experience</h4>
            <div className="mt-3 space-y-3">
              {profile.experiences.map(exp => (
                <div key={exp.id} className="border rounded-md p-3 bg-slate-50">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium">{exp.title} • {exp.company}</div>
                      <div className="text-sm text-slate-500">{exp.period}</div>
                    </div>
                    <div className="text-sm text-slate-400">{exp.desc}</div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="mt-6">
            <h4 className="text-lg font-semibold">Education</h4>
            <div className="mt-3 space-y-2">
              {profile.education.map(ed => (
                <div key={ed.id} className="text-sm text-slate-700">{ed.degree}, {ed.school} • {ed.period}</div>
              ))}
            </div>
          </div>

        </div>
      </div>

      {/* Use existing ProfileEditor component for editing */}
      {editing && (
        <div className="mt-6">
          <ProfileEditor
            profile={profile}
            onChange={setProfile}
            onSave={saveProfile}
            onCancel={() => setEditing(false)}
          />
        </div>
      )}
    </div>
  );
}

export default function LinkedInStyleAuthAndProfile() {
  const [userProfile, setUserProfile] = useState(null);

  function handleAuth(profile) {
    if (profile === null) {
      setUserProfile({ name: 'Guest', headline: 'Visitor', location: '', about: '', skills: [], experiences: [], education: [] });
    } else {
      setUserProfile(profile);
    }
  }

  function signOut() {
    setUserProfile(null);
  }

  return (
    <div className="min-h-screen bg-slate-50 p-8">
      <div className="max-w-6xl mx-auto">
        {!userProfile ? (
          <AuthCard onAuthenticate={handleAuth} />
        ) : (
          <ProfilePage profile={userProfile} onSignOut={signOut} />
        )}
      </div>
    </div>
  );
}
