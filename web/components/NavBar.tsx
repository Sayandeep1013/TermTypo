"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import type { User } from "@supabase/supabase-js";

export default function NavBar() {
  const [user, setUser] = useState<User | null>(null);
  const supabase = createClient();

  useEffect(() => {
    supabase.auth.getUser().then(({ data }) => setUser(data.user));
    const { data: sub } = supabase.auth.onAuthStateChange((_, s) =>
      setUser(s?.user ?? null)
    );
    return () => sub.subscription.unsubscribe();
  }, []);

  const signIn = async () => {
    await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: `${location.origin}/auth/callback` },
    });
  };

  const signOut = async () => {
    await supabase.auth.signOut();
    setUser(null);
  };

  return (
    <nav className="border-b border-[#2a2b3d] bg-[#1a1b26] px-6 py-3 flex items-center justify-between">
      {/* Logo */}
      <Link href="/" className="text-[#7aa2f7] font-bold text-lg tracking-widest hover:text-[#7dcfff] transition-colors">
        TERMTYPO
      </Link>

      {/* Nav links */}
      <div className="hidden sm:flex items-center gap-6 text-sm text-[#565f89]">
        <Link href="/play"        className="hover:text-[#c0caf5] transition-colors">play</Link>
        <Link href="/leaderboard" className="hover:text-[#c0caf5] transition-colors">leaderboard</Link>
        {user && (
          <Link href="/profile" className="hover:text-[#c0caf5] transition-colors">profile</Link>
        )}
        <a
          href="https://github.com/Sayandeep1013/TermTypo/releases/latest"
          target="_blank"
          rel="noopener"
          className="hover:text-[#c0caf5] transition-colors"
        >
          download
        </a>
      </div>

      {/* Auth */}
      <div className="text-sm">
        {user ? (
          <div className="flex items-center gap-3">
            <span className="text-[#565f89] hidden sm:inline truncate max-w-32">
              {user.user_metadata?.name || user.email}
            </span>
            <button
              onClick={signOut}
              className="text-[#f7768e] hover:text-[#ff9e9e] transition-colors"
            >
              logout
            </button>
          </div>
        ) : (
          <button
            onClick={signIn}
            className="text-[#9ece6a] hover:text-[#b5e884] transition-colors"
          >
            login
          </button>
        )}
      </div>
    </nav>
  );
}
