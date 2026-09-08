import { Blob, PaperStack, Sparkles } from "@/components/doodles";

export function EmptyIllustration({ size = 88, className }: { size?: number; className?: string }) {
  return (
    <div
      className={`relative inline-flex items-center justify-center ${className ?? ""}`}
      style={{ width: size, height: size * 0.9 }}
      aria-hidden="true"
    >
      <Blob className="absolute inset-0 h-full w-full text-foreground/[0.05]" />
      <PaperStack className="relative text-foreground/70" size={size * 0.62} />
      <Sparkles className="float absolute right-0 top-0 text-foreground/40" size={size * 0.24} />
    </div>
  );
}