"use client";
import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

const MODES = ["words_10","words_25","words_50","words_100","time_10","time_30","time_60"];
const WORDS = "the be to of and a in that have it for not on with he as you do at this but his by from they we say her she or an will my one all would there their what so up out if about who get which go me when make can like time no just him know take people into year your good some could them see other than then now look only come its over think also back after use two how our work first well way even new want because any these give day most us able above across act add afraid age ago agree air allow almost alone already".split(" ");

function makePassage(mode: string): string {
  const count = mode.startsWith("words_") ? parseInt(mode.split("_")[1]) : 80;
  const out: string[] = [];
  while (out.length < count) out.push(...[...WORDS].sort(() => Math.random() - 0.5));
  return out.slice(0, count).join(" ");
}

type View = "menu" | "create_waiting" | "join";

export default function RoomPage() {
  const [view,         setView]         = useState<View>("menu");
  const [selectedMode, setSelectedMode] = useState("words_50");
  const [roomCode,     setRoomCode]     = useState("");
  const [joinCode,     setJoinCode]     = useState("");
  const [error,        setError]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [loggedIn,     setLoggedIn]     = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const router  = useRouter();
  const sb      = createClient();

  useEffect(() => {
    sb.auth.getUser().then(({ data }) => setLoggedIn(!!data.user));
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);

  const createRoom = async () => {
    setLoading(true); setError("");
    const { data: { user } } = await sb.auth.getUser();
    if (!user) { setError("Not logged in."); setLoading(false); return; }
    const { data: code, error: err } = await sb.rpc("create_room", { p_host_id: user.id, p_mode: selectedMode });
    if (err || !code) { setError("Failed to create room."); setLoading(false); return; }
    setRoomCode(code);
    setView("create_waiting");
    setLoading(false);
    // Poll for guest joining
    pollRef.current = setInterval(async () => {
      const { data: room } = await sb.from("rooms").select("match_id, status").eq("code", code).maybeSingle();
      if (room?.status === "active" && room?.match_id) {
        if (pollRef.current) clearInterval(pollRef.current);
        router.push(`/race/${room.match_id}`);
      }
    }, 2000);
  };

  const joinRoom = async () => {
    if (joinCode.length !== 6) { setError("Code must be 6 characters."); return; }
    setLoading(true); setError("");
    const { data: { user } } = await sb.auth.getUser();
    if (!user) { setError("Not logged in."); setLoading(false); return; }
    // Check room exists first to get mode for passage generation
    const { data: room } = await sb.from("rooms").select("mode").eq("code", joinCode.toUpperCase()).eq("status","waiting").maybeSingle();
    if (!room) { setError("Room not found or already started."); setLoading(false); return; }
    const passage = makePassage(room.mode);
    const { data: result } = await sb.rpc("join_private_room", {
      p_code: joinCode.toUpperCase(),
      p_guest_id: user.id,
      p_passage: passage,
    });
    if (!result || result.error) { setError(result?.error || "Failed to join room."); setLoading(false); return; }
    router.push(`/race/${result.match_id}`);
  };

  if (!loggedIn) return (
    <div className="min-h-[calc(100vh-49px)] flex items-center justify-center">
      <div className="text-center space-y-4">
        <p className="text-[#565f89]">login required for private rooms</p>
        <button onClick={() => sb.auth.signInWithOAuth({ provider: "google", options: { redirectTo: `${location.origin}/auth/callback?next=/room` } })}
          className="px-6 py-2 border border-[#7aa2f7] text-[#7aa2f7] hover:bg-[#7aa2f7] hover:text-[#1a1b26] transition-all text-sm">
          login with google
        </button>
      </div>
    </div>
  );

  return (
    <div className="min-h-[calc(100vh-49px)] flex items-center justify-center">
      <div className="w-full max-w-sm border border-[#7aa2f7] bg-[#24283b] p-8 space-y-6">
        <div className="text-[#7aa2f7] text-xs uppercase tracking-widest">private room</div>

        {error && <p className="text-[#f7768e] text-xs">{error}</p>}

        {/* Menu */}
        {view === "menu" && (
          <div className="space-y-4">
            <div className="space-y-2 text-sm">
              <div className="text-xs text-[#565f89] uppercase tracking-widest mb-2">mode</div>
              {MODES.map(m => (
                <button key={m} onClick={() => setSelectedMode(m)}
                  className={`w-full text-left px-3 py-2 border transition-colors ${m === selectedMode
                    ? "border-[#7aa2f7] text-[#7aa2f7] bg-[#292e42]"
                    : "border-[#2a2b3d] hover:border-[#565f89] hover:text-[#c0caf5]"}`}>
                  {m}
                </button>
              ))}
            </div>
            <div className="flex gap-3">
              <button onClick={createRoom} disabled={loading}
                className="flex-1 py-2 border border-[#9ece6a] text-[#9ece6a] hover:bg-[#9ece6a] hover:text-[#1a1b26] transition-all text-sm disabled:opacity-50">
                create room
              </button>
              <button onClick={() => setView("join")}
                className="flex-1 py-2 border border-[#7dcfff] text-[#7dcfff] hover:bg-[#7dcfff] hover:text-[#1a1b26] transition-all text-sm">
                join room
              </button>
            </div>
          </div>
        )}

        {/* Waiting for guest */}
        {view === "create_waiting" && (
          <div className="space-y-4">
            <p className="text-[#565f89] text-sm">share this code with your friend</p>
            <div className="text-center text-2xl font-bold text-[#9ece6a] tracking-[0.4em] border border-[#2a2b3d] bg-[#1a1b26] py-4">
              {roomCode}
            </div>
            <p className="text-[#565f89] text-xs">waiting for them to join…</p>
            <button onClick={() => { if (pollRef.current) clearInterval(pollRef.current); setView("menu"); }}
              className="text-xs text-[#f7768e] hover:underline">cancel</button>
          </div>
        )}

        {/* Join */}
        {view === "join" && (
          <div className="space-y-4">
            <p className="text-[#565f89] text-sm">enter the 6-character room code</p>
            <input
              autoFocus
              value={joinCode}
              onChange={e => setJoinCode(e.target.value.toUpperCase().slice(0, 6))}
              onKeyDown={e => e.key === "Enter" && joinRoom()}
              placeholder="XXXXXX"
              className="w-full bg-[#1a1b26] border border-[#565f89] focus:border-[#7aa2f7] px-3 py-2 text-center text-lg tracking-[0.4em] outline-none text-[#c0caf5] font-mono placeholder-[#565f89]"
            />
            <div className="flex gap-3">
              <button onClick={joinRoom} disabled={loading || joinCode.length !== 6}
                className="flex-1 py-2 border border-[#9ece6a] text-[#9ece6a] hover:bg-[#9ece6a] hover:text-[#1a1b26] transition-all text-sm disabled:opacity-50">
                join
              </button>
              <button onClick={() => { setView("menu"); setError(""); }}
                className="px-4 py-2 border border-[#2a2b3d] text-[#565f89] hover:text-[#c0caf5] text-sm">
                back
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
