"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { RealtimeChannel } from "@supabase/supabase-js";

// ── pip-style progress bar ─────────────────────────────────────────────────────
function PipBar({ value, total, color }: { value: number; total: number; color: string }) {
  const pct  = Math.min(value / Math.max(total, 1), 1);
  const fill = Math.round(pct * 30);
  return (
    <span className="font-mono text-sm" style={{ color }}>
      {"━".repeat(fill)}
      <span style={{ color: "#2a2b3d" }}>{"░".repeat(30 - fill)}</span>
    </span>
  );
}

interface TypingState {
  words: string[];
  typed: string[][];
  curWord: number;
  started: boolean;
  finished: boolean;
  startTime: number;
  endTime: number;
  totalKeys: number;
  correctKeys: number;
}

function calcWpm(s: TypingState): number {
  const elapsed = (s.finished ? s.endTime : Date.now()) / 1000 - s.startTime / 1000;
  if (elapsed < 0.3) return 0;
  const correct = s.typed.slice(0, s.curWord).reduce((sum, t, i) =>
    sum + t.filter((c, j) => c === s.words[i]?.[j]).length, 0);
  return Math.round((correct / 5) / (elapsed / 60));
}

function calcAcc(s: TypingState): number {
  return s.totalKeys ? Math.round((s.correctKeys / s.totalKeys) * 100) : 100;
}

// ── main ──────────────────────────────────────────────────────────────────────
export default function RacePage() {
  const { matchId }       = useParams<{ matchId: string }>();
  const router            = useRouter();
  const sb                = createClient();

  const [matchData,   setMatchData]   = useState<{ mode: string; passage: string; is_ranked: boolean } | null>(null);
  const [myName,      setMyName]      = useState("You");
  const [oppName,     setOppName]     = useState("Opponent");
  const [myId,        setMyId]        = useState<string>("");
  const [oppProgress, setOppProgress] = useState({ typed: 0, wpm: 0, finished: false });
  const [result,      setResult]      = useState<{ won: boolean; wpm: number; acc: number; eloAfter?: number } | null>(null);

  const stateRef    = useRef<TypingState | null>(null);
  const channelRef  = useRef<RealtimeChannel | null>(null);
  const inputRef    = useRef<HTMLInputElement>(null);
  const bcastHandle = useRef<ReturnType<typeof setInterval> | null>(null);
  const finishedRef = useRef(false);
  const [display,   setDisplay]       = useState(0); // trigger re-render for typing area

  // ── load match ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const init = async () => {
      const { data: { user } } = await sb.auth.getUser();
      if (!user) { router.push("/ranked"); return; }
      setMyId(user.id);

      // My display name comes from auth metadata — always available
      const myDisplayName = user.user_metadata?.name
        || user.user_metadata?.full_name
        || user.email?.split("@")[0]
        || "You";
      setMyName(myDisplayName);

      const { data: match } = await sb
        .from("matches").select("mode, passage, is_ranked").eq("id", matchId).maybeSingle();
      if (!match) { router.push("/ranked"); return; }
      setMatchData(match);

      // Fetch participants and look up opponent name directly from profiles table
      const { data: parts } = await sb
        .from("match_participants")
        .select("user_id")
        .eq("match_id", matchId);

      const oppId = parts?.find(p => p.user_id !== user.id)?.user_id;
      if (oppId) {
        const { data: profile } = await sb
          .from("profiles")
          .select("username, display_name")
          .eq("id", oppId)
          .maybeSingle();
        setOppName(profile?.display_name || profile?.username || "Opponent");
      }

      const words = match.passage.split(" ");
      stateRef.current = {
        words, typed: [[]],
        curWord: 0, started: false, finished: false,
        startTime: 0, endTime: 0,
        totalKeys: 0, correctKeys: 0,
      };

      // Realtime channel
      const channel = sb.channel(`match:${matchId}`);
      channelRef.current = channel;
      channel
        .on("broadcast", { event: "progress" }, ({ payload }) => {
          if (payload.user_id !== user.id) {
            setOppProgress({ typed: payload.words_typed ?? 0, wpm: payload.wpm ?? 0, finished: payload.finished ?? false });
            if (payload.finished && !finishedRef.current) {
              // Opponent finished first — I lost
              finishRace(false);
            }
          }
        })
        .subscribe();

      setTimeout(() => inputRef.current?.focus(), 100);
    };
    init();
    return () => {
      if (channelRef.current) sb.removeChannel(channelRef.current);
      if (bcastHandle.current) clearInterval(bcastHandle.current);
    };
  }, [matchId]);

  // ── broadcast own progress ──────────────────────────────────────────────────
  const startBroadcast = useCallback(() => {
    bcastHandle.current = setInterval(() => {
      const s = stateRef.current;
      if (!s || !channelRef.current) return;
      channelRef.current.send({
        type: "broadcast", event: "progress",
        payload: { user_id: myId, words_typed: s.curWord, wpm: calcWpm(s), finished: false },
      });
    }, 200);
  }, [myId]);

  // ── finish race ─────────────────────────────────────────────────────────────
  const finishRace = useCallback(async (iWon: boolean) => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    if (bcastHandle.current) clearInterval(bcastHandle.current);

    const s = stateRef.current;
    if (!s) return;

    const wpm = calcWpm(s);
    const acc = calcAcc(s);

    // Broadcast final state
    if (channelRef.current) {
      channelRef.current.send({
        type: "broadcast", event: "progress",
        payload: { user_id: myId, words_typed: s.words.length, wpm, finished: true },
      });
    }

    // Call finish_match if I won (ranked)
    if (iWon && matchData?.is_ranked) {
      try {
        await sb.rpc("finish_match", {
          p_match_id:   matchId,
          p_winner_id:  myId,
          p_winner_wpm: wpm,
          p_winner_acc: acc,
          p_loser_wpm:  oppProgress.wpm,
          p_loser_acc:  100,
        });
      } catch {}
    }

    // Fetch updated ELO
    let eloAfter: number | undefined;
    if (matchData?.is_ranked) {
      const { data } = await sb.from("user_ratings")
        .select("elo").eq("user_id", myId).eq("mode", matchData.mode).maybeSingle();
      eloAfter = data?.elo;
    }

    setResult({ won: iWon, wpm, acc, eloAfter });
  }, [myId, matchData, matchId, oppProgress.wpm]);

  // ── keyboard handler ─────────────────────────────────────────────────────────
  const onKeyDown = useCallback((e: React.KeyboardEvent) => {
    const s = stateRef.current;
    if (!s || s.finished || result) return;
    if (e.key === "Escape") { router.push("/ranked"); return; }

    if (!s.started && e.key.length === 1 && e.key !== " ") {
      s.started = true;
      s.startTime = Date.now();
      startBroadcast();
    }
    if (!s.started) return;

    if (e.key === "Backspace") {
      e.preventDefault();
      if (s.typed[s.curWord]?.length) { s.typed[s.curWord].pop(); s.totalKeys++; }
      else if (s.curWord > 0) {
        s.curWord--;
        if (s.typed[s.curWord]?.length) { s.typed[s.curWord].pop(); s.totalKeys++; }
      }
      setDisplay(n => n + 1);
      return;
    }

    if (e.key === " ") {
      e.preventDefault();
      if (!s.typed[s.curWord]?.length) return;
      s.curWord++;
      s.totalKeys++;
      if (s.curWord >= s.words.length) { s.finished = true; s.endTime = Date.now(); finishRace(true); return; }
      if (!s.typed[s.curWord]) s.typed[s.curWord] = [];
      setDisplay(n => n + 1);
      return;
    }

    if (e.key.length === 1) {
      e.preventDefault();
      const wi = s.curWord;
      const ci = s.typed[wi]?.length ?? 0;
      const expected = s.words[wi]?.[ci];
      if (!s.typed[wi]) s.typed[wi] = [];
      s.typed[wi].push(e.key);
      s.totalKeys++;
      if (e.key === expected) s.correctKeys++;

      // Auto-finish on last word
      if (wi === s.words.length - 1 && s.typed[wi].join("") === s.words[wi]) {
        s.finished = true; s.endTime = Date.now();
        finishRace(true);
        return;
      }
      setDisplay(n => n + 1);
    }
  }, [result, startBroadcast, finishRace, router]);

  if (!matchData) return (
    <div className="min-h-[calc(100vh-49px)] flex items-center justify-center text-[#565f89]">
      loading race…
    </div>
  );

  const s = stateRef.current;
  const words = s?.words ?? [];
  const myWpm = s && s.started ? calcWpm(s) : 0;

  // ── render ──────────────────────────────────────────────────────────────────
  if (result) return (
    <div className="min-h-[calc(100vh-49px)] flex items-center justify-center">
      <div className="w-full max-w-sm border border-[#7aa2f7] bg-[#24283b] p-8 space-y-4">
        <div className={`text-lg font-bold ${result.won ? "text-[#9ece6a]" : "text-[#f7768e]"}`}>
          {result.won ? "VICTORY" : "DEFEAT"}
        </div>
        <div className="space-y-1 text-sm">
          <div><span className="text-[#565f89] w-24 inline-block">your wpm</span><span className="font-bold">{result.wpm}</span></div>
          <div><span className="text-[#565f89] w-24 inline-block">accuracy</span>{result.acc}%</div>
          {result.eloAfter !== undefined && (
            <div><span className="text-[#565f89] w-24 inline-block">elo now</span>
              <span className={result.won ? "text-[#9ece6a]" : "text-[#f7768e]"}>{result.eloAfter}</span>
            </div>
          )}
        </div>
        <div className="flex gap-4 text-xs">
          <button onClick={() => router.push("/ranked")} className="text-[#7aa2f7] hover:underline">ranked again</button>
          <button onClick={() => router.push("/")} className="text-[#565f89] hover:text-[#c0caf5]">home</button>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6" onClick={() => inputRef.current?.focus()}>
      {/* Header */}
      <div className="flex items-center justify-between text-xs text-[#565f89]">
        <span>{matchData.mode} · {matchData.is_ranked ? "ranked" : "private"}</span>
        {s?.started && <span className="text-[#9ece6a]">{myWpm} wpm</span>}
      </div>

      {/* Progress bars */}
      <div className="space-y-3 border border-[#2a2b3d] bg-[#24283b] p-4">
        <div className="flex items-center gap-3 text-sm">
          <span className="w-24 truncate text-[#7aa2f7]">{myName}</span>
          <PipBar value={s?.curWord ?? 0} total={words.length} color="#7aa2f7" />
          <span className="text-xs text-[#565f89] w-14 text-right">{myWpm} wpm</span>
        </div>
        <div className="flex items-center gap-3 text-sm">
          <span className="w-24 truncate text-[#565f89]">{oppName}</span>
          <PipBar value={oppProgress.typed} total={words.length} color="#565f89" />
          <span className="text-xs text-[#565f89] w-14 text-right">{oppProgress.wpm} wpm</span>
        </div>
      </div>

      {/* Typing area */}
      <div className="border border-[#2a2b3d] p-4 min-h-24 leading-8 text-base cursor-text select-none"
        style={{ fontFamily: "var(--font-mono)" }}>
        {words.map((word, wi) => {
          const t = s?.typed[wi] ?? [];
          const isCur = wi === (s?.curWord ?? 0);
          return (
            <span key={wi} className="mr-2 inline-block">
              {word.split("").map((ch, ci) => {
                const tc = t[ci];
                const cls = tc === undefined ? "text-[#565f89]"
                  : tc === ch ? "text-[#9ece6a]" : "text-[#f7768e]";
                return (
                  <span key={ci} className={`${cls} ${isCur && ci === t.length ? "border-l-2 border-[#7aa2f7]" : ""}`}>
                    {ch}
                  </span>
                );
              })}
              {t.slice(word.length).map((ch, i) => (
                <span key={`x${i}`} className="text-[#f7768e] bg-[#f7768e20]">{ch}</span>
              ))}
            </span>
          );
        })}
        {!s?.started && (
          <div className="absolute pointer-events-none text-[#565f89] text-sm mt-1">
            start typing to race…
          </div>
        )}
      </div>

      <input ref={inputRef} autoFocus onKeyDown={onKeyDown}
        className="sr-only" autoComplete="off" tabIndex={0} aria-label="race input" />

      <div className="text-xs text-[#565f89] text-center">
        <kbd className="bg-[#24283b] border border-[#2a2b3d] px-1.5 font-mono">esc</kbd> forfeit
      </div>
    </div>
  );
}
