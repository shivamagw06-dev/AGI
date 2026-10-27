import { Link, useLocation } from 'react-router-dom';
import { usePlus } from '@/contexts/PlusContext';
import { isPlusToolPath } from '@/lib/agiPlus';
import { useAuth } from '@/contexts/AuthContext';
import { buildLoginUrl } from '@/lib/accessPolicy';
import './plus.css';
export default function PaidAccessBoundary({children}){
 const location=useLocation(),plus=usePlus(),{user,authReady,loading}=useAuth();
 if(!isPlusToolPath(location.pathname))return children;
 if(loading||!authReady||plus.loading)return <main className="plus-page"><h1>Checking AGI Plus access…</h1></main>;
 if(plus.error)return <main className="plus-page"><h1>Access check unavailable</h1><p>{plus.error}</p><button onClick={plus.refresh}>Retry access check</button><Link to="/research">Read free articles</Link></main>;
 if(!plus.config?.enabled||((plus.active||plus.isAdmin)&&plus.subjectId===user?.id))return children;
 const next=location.pathname+location.search;
 return <main className="plus-page"><Link to="/">AGI home</Link><p className="plus-kicker">AGI PLUS</p><h1>Your research tools, in one membership.</h1><p>₹199 for 30 days. Articles remain free. Explore institutional holdings, screeners, portfolio tracking, market intelligence and Live Alpha with AGI Plus.</p><div className="plus-card"><h2>₹199 <small>/ 30 days</small></h2><p>Manual UPI payment · access after bank-credit verification · no automatic debit.</p><Link className="plus-primary" to={`/subscribe?next=${encodeURIComponent(next)}`}>{user?'Get or renew AGI Plus':'View membership and payment'}</Link>{!user&&<Link to={buildLoginUrl({returnTo:`/subscribe?next=${encodeURIComponent(next)}`,mode:'signin'})}>Already have access? Sign in</Link>}</div><Link to="/research">Continue reading free articles →</Link></main>;
}
