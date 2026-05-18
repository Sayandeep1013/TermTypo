"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

interface Command {
  id: string;
  label: string;
  hint: string;
  action: () => void;
}

export default function CommandPalette() {
  const [open,  setOpen]  = useState(false);
  const [query, setQuery] = useState("");
  const [idx,   setIdx]   = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const router   = useRouter();
  const sb       = createClient();

  const go = (path: string) => { setOpen(false); router.push(path); };

  const ALL_COMMANDS: Command[] = [
    { id: "play",        label: "play",        hint: "start typing",          action: () => go("/play") },
    { id: "leaderboard", label: "leaderboard", hint: "global rankings",       action: () => go("/leaderboard") },
    { id: "profile",     label: "profile",     hint: "your stats & ELO",      action: () => go("/profile") },
    { id: "home",        label: "home",        hint: "back to start",         action: () => go("/") },
    { id: "download",    label: "download",    hint: "Windows / macOS / Linux binary",
      action: () => { setOpen(false); window.open("https://github.com/Sayandeep1013/TermTypo/releases/latest", "_blank"); } },
    { id: "github",      label: "github",      hint: "source code",
      action: () => { setOpen(false); window.open("https://github.com/Sayandeep1013/TermTypo", "_blank"); } },
    { id: "logout",      label: "logout",      hint: "sign out",
      action: async () => { setOpen(false); await sb.auth.signOut(); router.refresh(); } },
  ];

  const filtered = query.trim()
    ? ALL_COMMANDS.filter(c =>
        c.label.includes(query.toLowerCase()) ||
        c.hint.toLowerCase().includes(query.toLowerCase())
      )
    : ALL_COMMANDS;

  // Reset index when query changes
  useEffect(() => setIdx(0), [query]);

  // Global keyboard listener
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      // Open: / (not in input) or Ctrl+K anywhere
      if ((e.key === "/" && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement))
          || (e.key === "k" && (e.ctrlKey || e.metaKey))) {
        e.preventDefault();
        setOpen(true);
        setQuery("");
        setIdx(0);
      }
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Auto-focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 20);
  }, [open]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setIdx(i => Math.min(i + 1, filtered.length - 1)); }
    if (e.key === "ArrowUp")   { e.preventDefault(); setIdx(i => Math.max(i - 1, 0)); }
    if (e.key === "Enter" && filtered[idx]) { filtered[idx].action(); setQuery(""); }
    if (e.key === "Escape") setOpen(false);
  };

  if (!open) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh] px-4"
      onClick={() => setOpen(false)}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60" />

      {/* Palette */}
      <div
        className="relative w-full max-w-md bg-[#24283b] border border-[#7aa2f7] shadow-2xl"
        onClick={e => e.stopPropagation()}
      >
        {/* Input row */}
        <div className="flex items-center border-b border-[#2a2b3d] px-3">
          <span className="text-[#7aa2f7] text-sm mr-2 select-none">›</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="type a command…"
            className="flex-1 bg-transparent py-3 text-sm text-[#c0caf5] placeholder-[#565f89] outline-none font-mono"
          />
          <kbd className="text-[10px] text-[#565f89] bg-[#1a1b26] border border-[#2a2b3d] px-1 py-0.5">esc</kbd>
        </div>

        {/* Results */}
        <ul className="max-h-64 overflow-y-auto py-1">
          {filtered.length === 0 ? (
            <li className="px-4 py-2.5 text-sm text-[#565f89]">no commands match</li>
          ) : (
            filtered.map((cmd, i) => (
              <li
                key={cmd.id}
                onClick={() => { cmd.action(); setQuery(""); }}
                className={`flex items-center justify-between px-4 py-2.5 cursor-pointer text-sm transition-colors ${
                  i === idx ? "bg-[#292e42]" : "hover:bg-[#292e42]"
                }`}
              >
                <span className={i === idx ? "text-[#7aa2f7]" : "text-[#c0caf5]"}>{cmd.label}</span>
                <span className="text-[#565f89] text-xs">{cmd.hint}</span>
              </li>
            ))
          )}
        </ul>

        {/* Footer hint */}
        <div className="border-t border-[#2a2b3d] px-4 py-2 flex gap-4 text-[10px] text-[#565f89]">
          <span><kbd className="bg-[#1a1b26] border border-[#2a2b3d] px-1">↑↓</kbd> navigate</span>
          <span><kbd className="bg-[#1a1b26] border border-[#2a2b3d] px-1">↵</kbd> select</span>
          <span><kbd className="bg-[#1a1b26] border border-[#2a2b3d] px-1">esc</kbd> close</span>
        </div>
      </div>
    </div>
  );
}
