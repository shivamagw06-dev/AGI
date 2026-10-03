import React, { useState } from "react";
import { supabase } from "@/lib/supabaseClient";
import { useNavigate } from "react-router-dom";
import { motion } from "framer-motion";
import { Mail, Lock, ArrowRight } from "lucide-react";

export default function AuthPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSignup, setIsSignup] = useState(false);
  const [msg, setMsg] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  async function handleSubmit(e) {
    e.preventDefault();
    setMsg("");
    setLoading(true);
    try {
      if (isSignup) {
        const { error } = await supabase.auth.signUp({ email, password });
        if (error) throw error;
        setMsg("✅ Check your email to confirm your sign-up.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
        navigate("/profile/edit");
      }
    } catch (err) {
      setMsg(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-gray-50 to-gray-100 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white shadow-xl rounded-2xl w-full max-w-md p-8 border border-gray-100"
      >
        <div className="text-center mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-1">
            {isSignup ? "Create Account" : "Welcome Back"}
          </h1>
          <p className="text-gray-500 text-sm">
            {isSignup
              ? "Join our community of investors and analysts."
              : "Log in to access your dashboard."}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <Mail className="absolute left-3 top-3 text-gray-400 w-5 h-5" />
            <input
              type="email"
              placeholder="Email address"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full border border-gray-300 rounded-lg pl-10 pr-3 py-2 focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 outline-none"
              required
            />
          </div>

          <div className="relative">
            <Lock className="absolute left-3 top-3 text-gray-400 w-5 h-5" />
            <input
              type="password"
              placeholder="Password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full border border-gray-300 rounded-lg pl-10 pr-3 py-2 focus:ring-2 focus:ring-yellow-400 focus:border-yellow-400 outline-none"
              required
            />
          </div>

          <button
            disabled={loading}
            className="w-full flex justify-center items-center gap-2 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold py-2.5 rounded-lg transition-colors"
          >
            {loading ? "Please wait..." : isSignup ? "Sign Up" : "Log In"}
            {!loading && <ArrowRight size={18} />}
          </button>
        </form>

        {msg && (
          <p className="text-center mt-4 text-sm text-red-600 bg-red-50 rounded-md py-2">
            {msg}
          </p>
        )}

        <p className="text-center text-sm text-gray-600 mt-5">
          {isSignup ? "Already have an account?" : "Don't have an account?"}{" "}
          <button
            onClick={() => setIsSignup(!isSignup)}
            className="text-yellow-600 hover:underline font-medium"
          >
            {isSignup ? "Log In" : "Sign Up"}
          </button>
        </p>

        <div className="mt-6 border-t pt-4">
          <p className="text-xs text-center text-gray-400 mb-2">
            or continue with
          </p>
          <div className="flex justify-center gap-3">
            <button className="border rounded-lg py-2 px-4 flex items-center gap-2 hover:bg-gray-50 transition">
              <img
                src="https://www.svgrepo.com/show/475656/google-color.svg"
                alt="Google"
                className="w-5 h-5"
              />
              Google
            </button>
            <button className="border rounded-lg py-2 px-4 flex items-center gap-2 hover:bg-gray-50 transition">
              <img
                src="https://www.svgrepo.com/show/448234/linkedin.svg"
                alt="LinkedIn"
                className="w-5 h-5"
              />
              LinkedIn
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
