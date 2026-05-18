import TypingTest from "@/components/TypingTest";

export const metadata = { title: "Play — TermTypo" };

export default function PlayPage() {
  return (
    <div className="min-h-[calc(100vh-49px)] flex flex-col items-center justify-center py-8">
      <TypingTest />
    </div>
  );
}
