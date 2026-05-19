"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import { createClient } from "@/lib/supabase/client";
import KeyboardViz from "@/components/KeyboardViz";

// ── word list (same pool as the terminal app) ─────────────────────────────────
const WORDS = `the be to of and a in that have it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us able above across act add afraid age ago agree air allow almost alone already although among animal another answer any anyone anything area arrive art ask away baby bad bag ball band base bear beat before begin behind believe beside better big bird bite black blue body book both bottom boy bring broken brother build burn busy call care carry cat catch cause change check child choice choose city clean clear climb close cold comment complete consider contain control cook cool count course cover cry cut dark dead deal dear decide deep different direct distance dog dry during early eat either else enough ever evil example except exist face fail fall family fast father feel file fill fire fish fly follow food friend full fun glad gone grow half hand happen hard head hear heart hide history hot human idea island join just key kind learn leave level life linger list little long love low mean meet mind miss money mother much must near never night north nothing notice now object often once order past patient plan point poor possible problem question read ready real reason record result river road role run same school sea second seem send set short should side sign slow small song south speak step stop story strong such sure system talk tell thought together top touch travel true try understand until very watch way while wish word write wrong year young`.split(" ").filter(Boolean);

function sample(n: number): string[] {
  const out: string[] = [];
  while (out.length < n) {
    out.push(...WORDS.sort(() => Math.random() - 0.5).slice(0, Math.min(n - out.length, WORDS.length)));
  }
  return out.slice(0, n);
}

const WORD_COUNTS = [10, 25, 50, 100] as const;
const TIME_OPTIONS = [10, 30, 60] as const;
type Mode = "words" | "time";

interface Result { wpm: number; rawWpm: number; accuracy: number; elapsed: number; wordCount: number; mode: string; }

// ── component ─────────────────────────────────────────────────────────────────
export default function TypingTest() {
  const [mode,       setMode]       = useState<Mode>("words");
  const [wordCount,  setWordCount]  = useState<number>(50);
  const [timeSec,    setTimeSec]    = useState<number>(30);
  const [words,      setWords]      = useState<string[]>(() => sample(50));
  const [typed,      setTyped]      = useState<string[][]>([[]]);
  const [curWord,    setCurWord]    = useState(0);
  const [started,    setStarted]    = useState(false);
  const [finished,   setFinished]   = useState(false);
  const [elapsed,    setElapsed]    = useState(0);
  const [result,     setResult]     = useState<Result | null>(null);
  const [lastChar,   setLastChar]   = useState("");
  const [lastCorrect,setLastCorrect]= useState(true);

  const startTime      = useRef<number>(0);
  const timerRef       = useRef<ReturnType<typeof setInterval> | null>(null);
  const inputRef       = useRef<HTMLInputElement>(null);
  const typingBoxRef   = useRef<HTMLDivElement>(null);
  const totalKeys      = useRef(0);
  const correctKeys    = useRef(0);
  const [halfWidth, setHalfWidth] = useState(0);

  useEffect(() => {
    const el = typingBoxRef.current;
    if (!el) return;
    const update = () => setHalfWidth(el.clientWidth / 2);
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const modeKey = mode === "words" ? `words_${wordCount}` : `time_${timeSec}`;

  // ── helpers ─────────────────────────────────────────────────────────────────
  const wpm = useCallback((el: number, correct: number) => {
    if (el < 0.3) return 0;
    return Math.round((correct / 5) / (el / 60));
  }, []);

  const reset = useCallback(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    const newWords = mode === "words" ? sample(wordCount) : sample(150);
    setWords(newWords);
    setTyped([[]]);
    setCurWord(0);
    setStarted(false);
    setFinished(false);
    setElapsed(0);
    setResult(null);
    totalKeys.current   = 0;
    correctKeys.current = 0;
    setTimeout(() => inputRef.current?.focus(), 50);
  }, [mode, wordCount, timeSec]);

  // Reset when mode/count changes
  useEffect(() => { reset(); }, [mode, wordCount, timeSec]);

  // ── finish ──────────────────────────────────────────────────────────────────
  const finish = useCallback((el: number, typedState: string[][], wordIdx: number) => {
    if (timerRef.current) clearInterval(timerRef.current);
    setFinished(true);
    const correctWords = typedState.slice(0, wordIdx).filter((t, i) => t.join("") === words[i]).length;
    const correctChars = typedState.slice(0, wordIdx).reduce((sum, t, i) =>
      sum + t.filter((c, j) => c === words[i]?.[j]).length, 0);
    const r: Result = {
      wpm:       wpm(el, correctChars),
      rawWpm:    Math.round((totalKeys.current / 5) / (el / 60)),
      accuracy:  totalKeys.current ? Math.round((correctKeys.current / totalKeys.current) * 100) : 100,
      elapsed:   el,
      wordCount: wordIdx,
      mode:      modeKey,
    };
    setResult(r);
    saveResult(r);
  }, [words, modeKey, wpm]);

  // ── timer tick ──────────────────────────────────────────────────────────────
  useEffect(() => {
    if (!started || finished) return;
    if (mode !== "time") return;
    timerRef.current = setInterval(() => {
      const el = (Date.now() - startTime.current) / 1000;
      setElapsed(el);
      if (el >= timeSec) {
        setElapsed(timeSec);
        // Capture current state via functional updater
        setTyped(prev => {
          finish(timeSec, prev, curWord);
          return prev;
        });
      }
    }, 100);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [started, finished, mode, timeSec, curWord, finish]);

  // ── keydown ─────────────────────────────────────────────────────────────────
  const onKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (finished) { if (e.key === "Tab") { e.preventDefault(); reset(); } return; }

    if (!started && e.key.length === 1 && e.key !== " ") {
      setStarted(true);
      startTime.current = Date.now();
    }
    if (!started) return;

    const el = (Date.now() - startTime.current) / 1000;

    // Tab always restarts — never lets focus leave the input
    if (e.key === "Tab") {
      e.preventDefault();
      reset();
      return;
    }

    if (e.key === "Backspace") {
      e.preventDefault();
      setTyped(prev => {
        const next = prev.map(a => [...a]);
        if (next[curWord]?.length) { next[curWord].pop(); }
        else if (curWord > 0) {
          setCurWord(w => w - 1);
          if (next[curWord - 1]?.length) next[curWord - 1].pop();
        }
        return next;
      });
      totalKeys.current++;
      return;
    }

    if (e.key === " ") {
      e.preventDefault();
      setLastChar(" ");
      setLastCorrect(true);
      if (!typed[curWord]?.length) return;
      const nextWord = curWord + 1;
      if (nextWord >= words.length) { finish(el, typed, nextWord); return; }
      setCurWord(nextWord);
      setTyped(prev => { const n = prev.map(a => [...a]); if (!n[nextWord]) n[nextWord] = []; return n; });
      totalKeys.current++;
      return;
    }

    if (e.key.length === 1) {
      e.preventDefault();
      const wi = curWord;
      const ci = typed[wi]?.length ?? 0;
      const expected = words[wi]?.[ci];
      const correct = e.key === expected;
      totalKeys.current++;
      if (correct) correctKeys.current++;
      // Update keyboard visualization
      setLastChar(e.key);
      setLastCorrect(correct);

      setTyped(prev => {
        const next = prev.map(a => [...a]);
        if (!next[wi]) next[wi] = [];
        next[wi].push(e.key);

        // Auto-finish: last word typed exactly
        if (wi === words.length - 1 && next[wi].join("") === words[wi]) {
          const elapsed2 = (Date.now() - startTime.current) / 1000;
          setTimeout(() => finish(elapsed2, next, wi + 1), 0);
        }
        return next;
      });
    }
  }, [finished, started, curWord, words, typed, reset, finish]);

  const saveResult = async (r: Result) => {
    const sb = createClient();
    const { data: { user } } = await sb.auth.getUser();
    if (!user) return;
    await sb.from("solo_results").insert({
      user_id: user.id, mode: r.mode, wpm: r.wpm, raw_wpm: r.rawWpm,
      accuracy: r.accuracy, word_count: r.wordCount, duration_seconds: Math.round(r.elapsed),
    });
  };

  // ── display time ────────────────────────────────────────────────────────────
  const remaining = Math.max(0, timeSec - elapsed);
  const liveWpm   = started && !finished ? wpm(elapsed || 0.1, correctKeys.current) : 0;
  const scrollChars = words.slice(0, curWord).reduce((sum, w) => sum + w.length + 1, 0)
    + (typed[curWord]?.length ?? 0);

  // ── render ──────────────────────────────────────────────────────────────────
  return (
    <div className="w-full max-w-3xl mx-auto px-4 py-8 space-y-6" onClick={() => inputRef.current?.focus()}>

      {/* Mode selector */}
      <div className="flex items-center gap-4 text-sm text-[#565f89]">
        <div className="flex gap-3">
          {(["words", "time"] as Mode[]).map(m => (
            <button key={m} onClick={() => setMode(m)} tabIndex={-1}
              className={`transition-colors ${mode === m ? "text-[#7aa2f7] underline underline-offset-4" : "hover:text-[#c0caf5]"}`}>
              {m}
            </button>
          ))}
        </div>
        <span className="text-[#2a2b3d]">│</span>
        {mode === "words" ? (
          <div className="flex gap-3">
            {WORD_COUNTS.map(n => (
              <button key={n} onClick={() => setWordCount(n)} tabIndex={-1}
                className={`transition-colors ${wordCount === n ? "text-[#7aa2f7] underline underline-offset-4" : "hover:text-[#c0caf5]"}`}>
                {n}
              </button>
            ))}
          </div>
        ) : (
          <div className="flex gap-3">
            {TIME_OPTIONS.map(t => (
              <button key={t} onClick={() => setTimeSec(t)} tabIndex={-1}
                className={`transition-colors ${timeSec === t ? "text-[#7aa2f7] underline underline-offset-4" : "hover:text-[#c0caf5]"}`}>
                {t}s
              </button>
            ))}
          </div>
        )}

        <div className="ml-auto text-xs">
          {started && !finished && (
            mode === "time"
              ? <span className={remaining < 5 ? "text-[#f7768e]" : "text-[#7dcfff]"}>{remaining.toFixed(1)}s</span>
              : <span className="text-[#9ece6a]">{liveWpm} wpm</span>
          )}
        </div>
      </div>

      {/* Words display — scrolling teleprompter */}
      {!result ? (
        <div
          ref={typingBoxRef}
          className="relative bg-[#1a1b26] border border-[#2a2b3d] px-4 overflow-hidden cursor-text select-none"
          style={{ fontFamily: "var(--font-mono)", height: "3rem", display: "flex", alignItems: "center" }}
        >
          <div
            className="flex items-center whitespace-nowrap transition-transform duration-75"
            style={{ transform: `translateX(calc(${halfWidth}px - ${scrollChars}ch))` }}
          >
            {words.map((word, wi) => {
              const t = typed[wi] ?? [];
              const isCurrent = wi === curWord;
              return (
                <span key={wi} className="mr-2 inline-flex">
                  {word.split("").map((ch, ci) => {
                    const typedCh = t[ci];
                    let cls = "text-[#565f89]";
                    if (typedCh !== undefined) {
                      cls = typedCh === ch ? "text-[#9ece6a]" : "text-[#f7768e]";
                    }
                    const isCursor = isCurrent && ci === t.length;
                    return (
                      <span key={ci} className={`${cls} ${isCursor ? "border-l-2 border-[#7aa2f7]" : ""}`}>
                        {ch}
                      </span>
                    );
                  })}
                  {t.slice(word.length).map((ch, i) => (
                    <span key={`extra-${i}`} className="text-[#f7768e] bg-[#f7768e20]">{ch}</span>
                  ))}
                </span>
              );
            })}
          </div>
          {!started && (
            <div className="absolute inset-0 flex items-center justify-center text-[#565f89] text-sm pointer-events-none">
              start typing to begin
            </div>
          )}
        </div>
      ) : (
        /* Results */
        <div className="border border-[#7aa2f7] bg-[#24283b] p-6 space-y-4 animate-fade-in">
          <div className="text-[#7aa2f7] text-xs uppercase tracking-widest">results</div>
          <div className="flex gap-8">
            <div>
              <div className="text-4xl font-bold text-[#9ece6a]">{result.wpm}</div>
              <div className="text-[#565f89] text-xs mt-1">wpm</div>
            </div>
            <div className="border-l border-[#2a2b3d] pl-8 space-y-1 text-sm">
              <div><span className="text-[#565f89]">raw wpm   </span><span>{result.rawWpm}</span></div>
              <div><span className="text-[#565f89]">accuracy  </span><span>{result.accuracy}%</span></div>
              <div><span className="text-[#565f89]">time      </span><span>{result.elapsed.toFixed(1)}s</span></div>
              <div><span className="text-[#565f89]">words     </span><span>{result.wordCount}</span></div>
            </div>
          </div>
          <div className="w-full bg-[#1a1b26] h-1.5 rounded-full overflow-hidden">
            <div className="bg-[#7aa2f7] h-full rounded-full" style={{ width: `${result.accuracy}%` }} />
          </div>
          <div className="text-xs text-[#565f89]">
            <button onClick={reset} className="text-[#9ece6a] hover:underline">retry</button>
            <span className="mx-2">·</span>
            <button onClick={() => { setMode("words"); setWordCount(50); reset(); }}
              className="hover:text-[#c0caf5] transition-colors">change mode</button>
          </div>
        </div>
      )}

      {/* Keyboard visualization */}
      {!result && <KeyboardViz lastChar={lastChar} lastCorrect={lastCorrect} />}

      {/*
        Hidden input that captures all keystrokes.
        - autoFocus: grabs focus the moment the page renders (first keypress works)
        - tabIndex={0}: browser Tab naturally loops back here (and we intercept Tab to restart)
        - onBlur: re-focuses after 80ms — recovers if user accidentally clicks away
          (timeout lets command palette / mode buttons receive their click first)
      */}
      <input
        ref={inputRef}
        autoFocus
        onKeyDown={onKeyDown}
        onBlur={() => {
          if (!result) setTimeout(() => inputRef.current?.focus(), 80);
        }}
        className="sr-only"
        autoComplete="off" autoCorrect="off" spellCheck="false"
        tabIndex={0}
        aria-label="typing input"
      />

      <div className="text-xs text-[#565f89] text-center">
        <kbd className="bg-[#24283b] border border-[#2a2b3d] px-1.5 py-0.5 font-mono">tab</kbd> restart
        {" · "}
        click anywhere to refocus
      </div>
    </div>
  );
}
