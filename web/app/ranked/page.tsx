"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import type { RealtimeChannel } from "@supabase/supabase-js";

const MODES = ["words_10","words_25","words_50","words_100","time_10","time_30","time_60"];
const SPINNER = ["⠋","⠙","⠸","⠴","⠦","⠇"];

// Same word pool as TypingTest
const WORDS = "the be to of and a in that have it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us able above across act add afraid age ago agree air allow almost alone already although among animal another answer any anyone anything area arrive art ask away baby bad bag ball band base bear beat before begin behind believe beside better big bird bite black blue body book both bottom boy bring broken brother build burn busy call care carry cat catch cause change check child choice choose city clean clear climb close cold comment complete consider contain control cook cool count course cover cry cut dark dead deal dear decide deep different direct distance dog dry during early eat either else enough ever evil example except exist face fail fall family fast father feel file fill fire fish fly follow food friend full fun glad gone grow half hand happen hard head hear heart hide history hot human idea island join just key kind learn leave level life linger list little long love low mean meet mind miss money mother much must near never night north nothing notice now object often once order past patient plan point poor possible problem question read ready real reason record result river road role run same school sea second seem send set short should side sign slow small song south speak step stop story strong such sure system talk tell thought together top touch travel true try understand until very watch way while wish word write wrong year young".split(" ");

function makePassage(mode: string): string {
  const count = mode.startsWith("words_") ? parseInt(mode.split("_")[1]) : 80;
  const out: string[] = [];
  while (out.length < count) out.push(...[...WORDS].sort(() => Math.random() - 0.5));
  return out.slice(0, count).join(" ");
}

export default function RankedPage() {
  const [selectedMode, setSelectedMode] = useState("words_50");
  const [status,       setStatus]       = useState<"select"|"searching"|"found">("select");
  const [tick,         setTick]         = useState(0);
  const [authChecked,  setAuthChecked]  = useState(false);
  const [loggedIn,     setLoggedIn]     = useState(false);
  const channelRef = useRef<RealtimeChannel | null>(null);
  const router     = useRouter();
  const sb         = createClient();

  useEffect(() => {
    sb.auth.getUser().then(({ data }) => {
      setLoggedIn(!!data.user);
      setAuthChecked(true);
    });
  }, []);

  useEffect(() => {
    if (status !== "searching") return;
    const t = setInterval(() => setTick(n => n + 1), 150);
    return () => clearInterval(t);
  }, [status]);

  const startSearch = async () => {
    const { data: { user } } = await sb.auth.getUser();
    if (!user) return;
    setStatus("searching");

    // Insert into queue
    await sb.from("matchmaking_queue").upsert({ user_id: user.id, mode: selectedMode, elo: 0 });

    const channel = sb.channel(`queue:${selectedMode}`);
    channelRef.current = channel;

    let creating = false;

    const handlePresence = async () => {
      if (creating) return;
      const state = channel.presenceState<{ user_id: string }>();
      const ids = [...new Set(Object.values(state).flat().map(p => p.user_id).filter(Boolean))];
      if (ids.length < 2) return;
      // Smallest UUID takes the host role (same as terminal app)
      if ([...ids].sort()[0] !== user.id) return;
      creating = true;
      const opponentId = ids.find(id => id !== user.id)!;
      const passage = makePassage(selectedMode);
      const { data: matchId } = await sb.rpc("create_match_from_queue", {
        p_user1_id: user.id,
        p_user2_id: opponentId,
        p_mode: selectedMode,
        p_passage: passage,
      });
      if (matchId) {
        await channel.send({ type: "broadcast", event: "match_found", payload: { match_id: matchId } });
        setStatus("found");
        router.push(`/race/${matchId}`);
      } else {
        creating = false;
      }
    };

    channel
      .on("broadcast", { event: "match_found" }, ({ payload }) => {
        if (payload.match_id) { setStatus("found"); router.push(`/race/${payload.match_id}`); }
      })
      .on("presence", { event: "join" },  handlePresence)
      .on("presence", { event: "sync" },  handlePresence)
      .subscribe(async (s) => {
        if (s === "SUBSCRIBED") await channel.track({ user_id: user.id });
      });
  };

  const cancel = async () => {
    const { data: { user } } = await sb.auth.getUser();
    if (user) await sb.from("matchmaking_queue").delete().eq("user_id", user.id);
    if (channelRef.current) sb.removeChannel(channelRef.current);
    setStatus("select");
  };

  useEffect(() => () => { cancel(); }, []);

  if (!authChecked) return null;
  if (!loggedIn) return (
    <div className="min-h-[calc(100vh-49px)] flex items-center justify-center">
      <div className="text-center space-y-4">
        <p className="text-[#565f89]">login required for ranked matches</p>
        <button onClick={() => sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: `${location.origin}/auth/callback?next=/ranked` } })}
          className="px-6 py-2 border border-[#7aa2f7] text-[#7aa2f7] hover:bg-[#7aa2f7] hover:text-[#1a1b26] transition-all text-sm">
          login with google
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-[calc(100vh-49px)] flex items-center justify-center">
      <div className="w-full max-w-sm border border-[#7aa2f7] bg-[#24283b] p-8 space-y-6">
        <div className="text-[#7aa2f7] text-xs uppercase tracking-widest">ranked match</div>

        {status === "select" && (<>
          <div className="space-y-2 text-sm text-[#565f89]">
            <div className="text-xs uppercase tracking-widest mb-3">select mode</div>
            {MODES.map(m => (
              <button key={m} onClick={() => setSelectedMode(m)}
                className={`w-full text-left px-3 py-2 border transition-colors ${m === selectedMode
                  ? "border-[#7aa2f7] text-[#7aa2f7] bg-[#292e42]"
                  : "border-[#2a2b3d] hover:border-[#565f89] hover:text-[#c0caf5]"}`}>
                {m}
              </button>
            ))}
          </div>
          <button onClick={startSearch}
            className="w-full py-2 border border-[#9ece6a] text-[#9ece6a] hover:bg-[#9ece6a] hover:text-[#1a1b26] transition-all text-sm">
            find opponent
          </button>
        </>)}

        {status === "searching" && (
          <div className="space-y-4">
            <div className="text-[#565f89] text-sm">
              mode <span className="text-[#c0caf5]">{selectedMode}</span>
            </div>
            <div className="flex items-center gap-2 text-[#7aa2f7]">
              <span>{SPINNER[tick % SPINNER.length]}</span>
              <span className="text-sm text-[#565f89]">searching for opponent…</span>
            </div>
            <button onClick={cancel} className="text-xs text-[#f7768e] hover:underline">cancel</button>
          </div>
        )}

        {status === "found" && (
          <div className="text-[#9ece6a] text-sm">opponent found — loading race…</div>
        )}
      </div>
    </div>
  );
}
