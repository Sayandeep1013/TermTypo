import { createClient } from "@/lib/supabase/server";

export const metadata = { title: "Leaderboard — TermTypo" };
export const revalidate = 60; // ISR: refresh every 60s

const MODES = ["words_10","words_25","words_50","words_100","time_10","time_30","time_60"];

const TIERS = [
  { min: 1500, name: "Master",   color: "#e0af68" },
  { min: 1200, name: "Diamond",  color: "#7dcfff" },
  { min:  900, name: "Platinum", color: "#9ece6a" },
  { min:  600, name: "Gold",     color: "#e0af68" },
  { min:  300, name: "Silver",   color: "#c0caf5" },
  { min:    0, name: "Bronze",   color: "#bb9af7" },
];

function rankLabel(elo: number) {
  const t = TIERS.find(t => elo >= t.min) ?? TIERS[TIERS.length - 1];
  const sub = t.min >= 1200 ? "" : ` ${"I".repeat(Math.min((elo - t.min) / 100 | 0, 2) + 1)}`;
  return { label: t.name + sub, color: t.color };
}

export default async function LeaderboardPage({
  searchParams,
}: {
  searchParams: Promise<{ mode?: string }>;
}) {
  const { mode: modeParam } = await searchParams;
  const mode = MODES.includes(modeParam ?? "") ? modeParam! : "words_50";

  const sb = await createClient();
  const { data } = await sb
    .from("user_ratings")
    .select("elo, wins, losses, user_id, profiles(username, display_name)")
    .eq("mode", mode)
    .order("elo", { ascending: false })
    .limit(25);

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <h1 className="text-[#7aa2f7] text-sm uppercase tracking-widest mb-6">leaderboard</h1>

      {/* Mode tabs */}
      <div className="flex flex-wrap gap-3 text-xs text-[#565f89] mb-6 border-b border-[#2a2b3d] pb-4">
        {MODES.map(m => (
          <a
            key={m}
            href={`/leaderboard?mode=${m}`}
            className={`transition-colors ${m === mode
              ? "text-[#7aa2f7] underline underline-offset-4"
              : "hover:text-[#c0caf5]"}`}
          >
            {m}
          </a>
        ))}
      </div>

      {/* Table */}
      {!data?.length ? (
        <p className="text-[#565f89] text-sm">
          No players ranked yet in {mode}.<br />
          Complete a ranked match to appear here.
        </p>
      ) : (
        <table className="w-full text-sm border-collapse">
          <thead>
            <tr className="text-[#565f89] text-xs border-b border-[#2a2b3d]">
              <th className="text-left py-2 w-8">#</th>
              <th className="text-left py-2">player</th>
              <th className="text-left py-2">rank</th>
              <th className="text-right py-2">elo</th>
              <th className="text-right py-2">w</th>
              <th className="text-right py-2">l</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row, i) => {
              const profile = row.profiles as { username?: string; display_name?: string } | null;
              const name = profile?.display_name || profile?.username || "—";
              const { label, color } = rankLabel(row.elo);
              const wl = row.wins + row.losses > 0
                ? `${Math.round(row.wins / (row.wins + row.losses) * 100)}%`
                : "—";
              return (
                <tr key={row.user_id} className="border-b border-[#2a2b3d] hover:bg-[#24283b] transition-colors">
                  <td className="py-2 text-[#565f89]">{i + 1}</td>
                  <td className="py-2 text-[#c0caf5]">{name}</td>
                  <td className="py-2" style={{ color }}>{label}</td>
                  <td className="py-2 text-right">{row.elo}</td>
                  <td className="py-2 text-right text-[#9ece6a]">{row.wins}</td>
                  <td className="py-2 text-right text-[#f7768e]">{row.losses}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
