import Link from "next/link";

const LOGO = [
  " ████████╗███████╗██████╗ ███╗   ███╗",
  "    ██╔══╝██╔════╝██╔══██╗████╗ ████║",
  "    ██║   █████╗  ██████╔╝██╔████╔██║",
  "    ██║   ██╔══╝  ██╔══██╗██║╚██╔╝██║",
  "    ██║   ███████╗██║  ██║██║ ╚═╝ ██║",
  "    ╚═╝   ╚══════╝╚═╝  ╚═╝╚═╝     ╚═╝",
  " ████████╗██╗   ██╗██████╗  ██████╗",
  "    ██╔══╝ ██╗ ██╔╝██╔══██╗██╔═══██╗",
  "    ██║    ╚████╔╝ ██████╔╝██║   ██║",
  "    ██║     ╚██╔╝  ██╔═══╝ ██║   ██║",
  "    ██║      ██║   ██║     ╚██████╔╝",
  "    ╚═╝      ╚═╝   ╚═╝      ╚═════╝",
];

const FEATURES = [
  { key: "solo",      label: "solo practice",  desc: "10 modes — words & timed. WPM, accuracy, history." },
  { key: "ranked",    label: "ranked matches",  desc: "1v1 race. ELO ladder. Bronze to Master." },
  { key: "rooms",     label: "private rooms",   desc: "6-char code. Race your friends. No ELO change." },
  { key: "cross",     label: "cross-platform",  desc: "Web, Windows, macOS, Linux — same account." },
];

export default function HomePage() {
  return (
    <div className="min-h-[calc(100vh-49px)] flex flex-col items-center justify-center px-4 py-16 gap-12">

      {/* ASCII logo */}
      <div className="text-center">
        <pre className="text-[#7aa2f7] text-xs sm:text-sm leading-tight select-none inline-block text-left">
          {LOGO.map((line, i) => {
            // Color the block chars bright, box-drawing chars dim
            const parts = line.split("").map((ch, j) => (
              ch === "█"
                ? <span key={j} className="text-[#7aa2f7]">{ch}</span>
                : <span key={j} className="text-[#2a2d4a]">{ch}</span>
            ));
            return <div key={i}>{parts}</div>;
          })}
        </pre>
        <p className="text-[#565f89] text-sm mt-4 tracking-widest uppercase">
          type · race · rank
        </p>
      </div>

      {/* CTA buttons */}
      <div className="flex flex-wrap items-center justify-center gap-4">
        <Link
          href="/play"
          className="px-6 py-2 border border-[#7aa2f7] text-[#7aa2f7] hover:bg-[#7aa2f7] hover:text-[#1a1b26] transition-all text-sm"
        >
          play in browser
        </Link>
        <a
          href="https://github.com/Sayandeep1013/TermTypo/releases/latest"
          target="_blank"
          rel="noopener"
          className="px-6 py-2 border border-[#565f89] text-[#565f89] hover:border-[#9ece6a] hover:text-[#9ece6a] transition-all text-sm"
        >
          download app
        </a>
        <code className="text-xs text-[#565f89] bg-[#24283b] px-3 py-2 border border-[#2a2b3d]">
          pip install termtypo
        </code>
      </div>

      {/* Feature grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl w-full">
        {FEATURES.map((f) => (
          <div
            key={f.key}
            className="border border-[#2a2b3d] bg-[#24283b] p-4 hover:border-[#7aa2f7] transition-colors"
          >
            <div className="text-[#7aa2f7] text-xs mb-1 tracking-widest uppercase">{f.label}</div>
            <div className="text-[#565f89] text-xs leading-relaxed">{f.desc}</div>
          </div>
        ))}
      </div>

      {/* Install hint */}
      <div className="text-center text-xs text-[#565f89] space-y-1">
        <p>All platforms share the same backend — same account, same ELO, same leaderboard.</p>
        <p>
          <a href="https://github.com/Sayandeep1013/TermTypo" target="_blank" rel="noopener"
             className="text-[#7aa2f7] hover:underline">
            github.com/Sayandeep1013/TermTypo
          </a>
        </p>
      </div>
    </div>
  );
}
