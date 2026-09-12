import { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Loader2 } from 'lucide-react';
import { Link } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useToast } from '@/components/ui/use-toast';
import { subscribeNewsletter } from '@/lib/subscribeNewsletter';

export default function Newsletter() {
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const { toast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
      await subscribeNewsletter(email);
      toast({
        title: 'Subscribed successfully',
        description: 'You will receive our latest research and market updates.',
        duration: 4000,
      });
      setEmail('');
    } catch (err) {
      toast({
        title: 'Could not subscribe',
        description: err.message || 'Please try again later.',
        variant: 'destructive',
        duration: 4000,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <section id="newsletter" className="py-20 bg-slate-900 border-t border-white/10">
      <div className="max-w-4xl mx-auto px-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-center"
        >
          <div className="inline-flex rounded-full bg-blue-600/20 border border-blue-500/30 p-3 mb-6">
            <Mail className="h-7 w-7 text-blue-400" />
          </div>

          <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
            Research delivered to your inbox
          </h2>

          <p className="text-lg text-slate-400 mb-8 max-w-2xl mx-auto">
            Get notified when we publish new macro notes, equity research, and private markets analysis.
          </p>

          <form onSubmit={handleSubmit} className="flex flex-col sm:flex-row gap-3 max-w-lg mx-auto">
            <Input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@company.com"
              disabled={loading}
              className="flex-1 h-12 bg-slate-950 border-white/15 text-white placeholder:text-slate-500"
            />
            <Button
              type="submit"
              disabled={loading}
              className="h-12 px-8 bg-blue-600 hover:bg-blue-700 font-semibold shrink-0"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Subscribing…
                </>
              ) : (
                'Subscribe'
              )}
            </Button>
          </form>

          <p className="text-xs text-slate-500 mt-4">
            No spam. Unsubscribe anytime. See our{' '}
            <Link to="/privacy" className="text-blue-400 hover:underline">
              Privacy Policy
            </Link>
            .
          </p>
        </motion.div>
      </div>
    </section>
  );
}
