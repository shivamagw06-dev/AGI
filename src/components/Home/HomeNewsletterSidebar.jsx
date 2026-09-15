import { useState } from 'react';
import { Mail, Loader2 } from 'lucide-react';
import { useToast } from '@/components/ui/use-toast';
import { subscribeNewsletter } from '@/lib/subscribeNewsletter';

export default function HomeNewsletterSidebar() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await subscribeNewsletter(email);
      toast({ title: 'Subscribed', description: 'Check your inbox for a welcome email.' });
      setEmail('');
    } catch (err) {
      toast({
        title: 'Subscription failed',
        description: err.message,
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="border border-[#dddddd] bg-[#fafafa] p-4">
      <div className="flex items-start gap-3">
        <div className="shrink-0 w-10 h-10 bg-[#111111] flex items-center justify-center">
          <Mail className="w-5 h-5 text-white" />
        </div>
        <div className="min-w-0 flex-1">
          <h3 className="text-sm font-bold text-[#111111] leading-snug">
            AGI Research Brief
          </h3>
          <p className="text-xs text-[#555555] mt-1 leading-relaxed">
            Daily market updates and research delivered to your inbox.
          </p>
          <form onSubmit={handleSubmit} className="mt-3 space-y-2">
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="Email address"
              disabled={loading}
              className="w-full border border-[#cccccc] px-2.5 py-2 text-xs text-[#111111] placeholder:text-[#999] focus:border-[#111111] focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#111111] text-white text-xs font-bold py-2 hover:bg-[#333] transition-colors disabled:opacity-60"
            >
              {loading ? 'Signing up…' : 'Sign up'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
