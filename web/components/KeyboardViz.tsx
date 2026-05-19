"use client";
import { useEffect, useRef } from "react";

const ROWS = [
  ["q","w","e","r","t","y","u","i","o","p"],
  ["a","s","d","f","g","h","j","k","l"],
  ["z","x","c","v","b","n","m"],
];

// indents to give QWERTY stagger
const INDENTS = ["0rem", "0.7rem", "1.6rem"];

interface Props {
  lastChar:    string;
  lastCorrect: boolean;
}

export default function KeyboardViz({ lastChar, lastCorrect }: Props) {
  const key = lastChar.toLowerCase();

  return (
    <div className="flex flex-col items-center gap-1 py-2 select-none">
      {ROWS.map((row, ri) => (
        <div key={ri} className="flex gap-1" style={{ paddingLeft: INDENTS[ri] }}>
          {row.map(k => {
            const active = k === key;
            return (
              <div
                key={k}
                className={`w-7 h-7 flex items-center justify-center text-xs font-mono border rounded-sm transition-all duration-75 ${
                  active
                    ? lastCorrect
                      ? "border-[#9ece6a] text-[#9ece6a] bg-[#9ece6a15] shadow-[0_0_6px_#9ece6a40]"
                      : "border-[#f7768e] text-[#f7768e] bg-[#f7768e15] shadow-[0_0_6px_#f7768e40]"
                    : "border-[#2a2b3d] text-[#565f89]"
                }`}
              >
                {k.toUpperCase()}
              </div>
            );
          })}
        </div>
      ))}

      {/* Space bar */}
      <div
        className={`h-6 flex items-center justify-center text-xs font-mono border rounded-sm transition-all duration-75 ${
          key === " "
            ? lastCorrect
              ? "border-[#9ece6a] text-[#9ece6a] bg-[#9ece6a15]"
              : "border-[#f7768e] text-[#f7768e] bg-[#f7768e15]"
            : "border-[#2a2b3d] text-[#565f89]"
        }`}
        style={{ width: "14rem" }}
      >
        space
      </div>
    </div>
  );
}
