import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Profile — TermTypo" };

const MODE_ORDER = ["words_10","words_25","words_50","words_100","time_10","time_30","time_60"];
const TIERS = [
  { min: 1500, name: "Master",   color: "#e0af68" },
  { min: 1200, name: "Diamond",  color: "#7dcfff" },
  { min:  900, name: "Platinum", color: "#9ece6a" },
  { min:  600, name: "Gold",     color: "#e0af68" },
  { min:  300, name: "Silver",   color: "#c0caf5" },
  { min:    0, name: "Bronze",   color: "#bb9af7" },
];
function rank(elo: number) {
  const t = TIERS.find(t => elo >= t.min) ?? TIERS[TIERS.length - 1];
  const sub = t.min >= 1200 ? "" : ` ${"I".repeat(Math.min((elo - t.min) / 100 | 0, 2) + 1)}`;
  return { label: t.name + sub, color: t.color };
}
function bar(v: number, max = 300) {
  return Math.min((v / max) * 100, 100);
}

export default async function ProfilePage() {
  const sb = await createClient();
  const { data: { user } } = await sb.auth.getUser();
  if (!user) redirect("/");

  const [{ data: ratings }, { data: recent }, { data: best }] = await Promise.all([
    sb.from("user_ratings").select("mode, elo, wins, losses").eq("user_id", user.id),
    sb.from("solo_results").select("mode, wpm, raw_wpm, accuracy, created_at")
      .eq("user_id", user.id).order("created_at", { ascending: false }).limit(10),
    sb.from("solo_results").select("mode, wpm")
      .eq("user_id", user.id).order("wpm", { ascending: false }).limit(1),
  ]);

  const ratingsMap = Object.fromEntries((ratings ?? []).map(r => [r.mode, r]));
  const name = user.user_metadata?.name || user.email;
  const bestResult = best?.[0];

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">

      {/* Header */}
      <div className="border-b border-[#2a2b3d] pb-4">
        <div className="text-[#7aa2f7] font-bold text-lg">{name}</div>
        <div className="text-[#565f89] text-sm">{user.email}</div>
        {bestResult && (
          <div className="mt-2 text-sm">
            <span className="text-[#565f89]">personal best  </span>
            <span className="text-[#9ece6a] font-bold">{bestResult.wpm} wpm</span>
            <span className="text-[#565f89]"> ({bestResult.mode})</span>
          </div>
        )}
      </div>

      {/* Ratings */}
      <div>
        <h2 className="text-[#7aa2f7] text-xs uppercase tracking-widest mb-3">ratings</h2>
        <div className="space-y-2">
          {MODE_ORDER.map(mode => {
            const r = ratingsMap[mode];
            const { label, color } = r ? rank(r.elo) : rank(0);
            const progress = r ? bar(r.elo % 300) : 0;
            return (
              <div key={mode} className="flex items-center gap-3 text-sm">
                <span className="text-[#565f89] w-24 shrink-0">{mode}</span>
                <span style={{ color }} className="w-28 shrink-0">{r ? label : "Unranked"}</span>
                <span className="text-[#c0caf5] w-12 text-right shrink-0">{r?.elo ?? "—"}</span>
                <div className="flex-1 bg-[#24283b] h-1 rounded-full overflow-hidden">
                  {r && <div className="bg-[#7aa2f7] h-full rounded-full" style={{ width: `${progress}%` }} />}
                </div>
                <span className="text-[#9ece6a] text-xs w-8 text-right shrink-0">{r?.wins ?? 0}W</span>
                <span className="text-[#f7768e] text-xs w-8 text-right shrink-0">{r?.losses ?? 0}L</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Recent solo */}
      <div>
        <h2 className="text-[#7aa2f7] text-xs uppercase tracking-widest mb-3">recent solo</h2>
        {!recent?.length ? (
          <p className="text-[#565f89] text-sm">No solo results yet. Play in the browser or terminal app.</p>
        ) : (
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="text-[#565f89] text-xs border-b border-[#2a2b3d]">
                <th className="text-left py-2">mode</th>
                <th className="text-right py-2">wpm</th>
                <th className="text-right py-2">raw</th>
                <th className="text-right py-2">acc</th>
              </tr>
            </thead>
            <tbody>
              {recent.map((r, i) => (
                <tr key={i} className="border-b border-[#2a2b3d] hover:bg-[#24283b] transition-colors">
                  <td className="py-2 text-[#565f89]">{r.mode}</td>
                  <td className="py-2 text-right font-bold">{r.wpm}</td>
                  <td className="py-2 text-right text-[#565f89]">{r.raw_wpm}</td>
                  <td className="py-2 text-right text-[#7aa2f7]">{r.accuracy}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
