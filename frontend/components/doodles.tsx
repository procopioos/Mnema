import type { SVGProps } from "react";

type DoodleProps = SVGProps<SVGSVGElement> & {
  size?: number;
};

export function RoughFilter() {
  return (
    <svg width="0" height="0" aria-hidden="true" focusable="false">
      <defs>
        <filter id="mnema-rough">
          <feTurbulence type="fractalNoise" baseFrequency="0.055" numOctaves="3" result="noise" seed="3" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale="1.6" />
        </filter>
      </defs>
    </svg>
  );
}

const UNDERLINE_D =
  "M 4 6.2 Q 7.5 1.8 11.5 6.2 Q 14.5 9.4 19 6.2 Q 22 1.2 27.5 6.2 Q 30.5 8.8 35 6.2 Q 39 0.8 45 6.2 Q 49 9 54 6.2 Q 58 2 64 6.2 Q 68 8.5 74 6.2 Q 78.5 1.4 84 6.2 Q 88 9.2 94 6.2 Q 98 2.2 104 6.2 Q 108 8 112 6.2 Q 116 3.5 118 4.2";

export function WavyUnderline({ size = 120, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={(size * 10) / 120}
      viewBox="0 0 120 10"
      fill="none"
      stroke="currentColor"
      strokeWidth={2.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      vectorEffect="non-scaling-stroke"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <path d={UNDERLINE_D} />
    </svg>
  );
}

export function Sparkles({ size = 24, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 36 36"
      fill="currentColor"
      stroke="none"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <path d="M 15 4 L 17.4 12.6 L 26 15 L 17.4 17.4 L 15 26 L 12.6 17.4 L 4 15 L 12.6 12.6 Z" />
      <path opacity="0.7" d="M 31 22 L 32.5 27.5 L 38 29 L 32.5 30.5 L 31 36 L 29.5 30.5 L 24 29 L 29.5 27.5 Z" />
      <path opacity="0.45" d="M 21 30 L 21.8 33.2 L 25 34 L 21.8 34.8 L 21 38 L 20.2 34.8 L 17 34 L 20.2 33.2 Z" />
    </svg>
  );
}

export function PaperStack({ size = 96, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={(size * 96) / 100}
      viewBox="0 0 100 96"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#mnema-rough)"
      >
        <rect x="22" y="16" width="50" height="62" rx="6" transform="rotate(-7 47 47)" opacity="0.55" />
        <rect x="32" y="10" width="50" height="62" rx="6" transform="rotate(4 57 41)" opacity="0.75" />
        <rect x="25" y="22" width="50" height="62" rx="6" />
        <path d="M 33 42 Q 44 38 67 44" strokeWidth={1.5} />
        <path d="M 33 52 Q 46 48 67 54" strokeWidth={1.5} />
        <path d="M 33 62 Q 44 58 67 64" strokeWidth={1.5} />
        <path d="M 71 22 L 71 33 L 59 33 Z" opacity="0.8" />
      </g>
    </svg>
  );
}

export function FolderFace({ size = 96, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={(size * 84) / 100}
      viewBox="0 0 100 84"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <g
        fill="none"
        stroke="currentColor"
        strokeWidth={2}
        strokeLinecap="round"
        strokeLinejoin="round"
        filter="url(#mnema-rough)"
      >
        <path d="M 8 20 C 8 17 10 15 13 15 H 36 L 45 24 H 87 C 91 24 93 26 93 30 V 68 C 93 72 90 75 86 75 H 13 C 9 75 7 72 7 68 Z" />
        <path d="M 7 36 H 93" opacity="0.6" />
        <circle cx="34" cy="50" r="2.6" fill="currentColor" stroke="none" />
        <circle cx="57" cy="50" r="2.6" fill="currentColor" stroke="none" />
        <path d="M 42 58 Q 47 64 51 58 T 60 58" strokeWidth={1.6} />
      </g>
    </svg>
  );
}

const BLOB_PATH =
  "M 96 18 C 132 12 176 32 184 70 C 192 96 178 128 148 144 C 118 154 78 152 48 130 C 28 104 32 68 64 42 C 76 30 84 20 96 18 Z";

export function Blob({ size = 64, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={(size * 160) / 200}
      viewBox="0 0 200 160"
      fill="currentColor"
      stroke="currentColor"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <path d={BLOB_PATH} filter="url(#mnema-rough)" />
      <path d={BLOB_PATH} fill="none" strokeWidth={1.8} strokeDasharray="6 10" opacity="0.45" transform="translate(1.2 0.8)" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

export function Confetti({ size = 24, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={(size * 96) / 120}
      viewBox="0 0 120 96"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <g fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round">
        <path d="M 46 58 L 40 66" />
        <path d="M 74 60 L 80 66" />
        <path d="M 30 74 L 20 76" />
        <path d="M 92 74 L 102 70" />
        <path d="M 60 86 L 60 96" />
        <path d="M 44 82 L 34 90" />
        <path d="M 78 82 L 88 90" strokeWidth={1.6} />
        <path d="M 62 60 L 68 52" strokeWidth={1.6} />
      </g>
      <circle cx="58" cy="48" r="2.4" fill="currentColor" stroke="none" />
      <circle cx="84" cy="52" r="1.8" fill="currentColor" stroke="none" opacity="0.7" />
    </svg>
  );
}

export function ScribbleArrow({ size = 24, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 64 64"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <g fill="none" stroke="currentColor" strokeWidth={2.4} strokeLinecap="round" strokeLinejoin="round">
        <path d="M 12 50 Q 32 52 40 40 Q 48 26 40 18 Q 50 12 56 18" />
        <path d="M 56 18 L 50 26 M 56 18 L 44 20" />
      </g>
    </svg>
  );
}

const WAVE_PATH = (() => {
  const w = 1440;
  const seg = 72;
  const amp = 5;
  let d = `M 0 ${amp} Q ${seg / 2} 0 ${seg} ${amp}`;
  for (let x = seg * 2; x <= w; x += seg * 2) d += ` T ${x} ${amp}`;
  return d;
})();

export function WavyDivider({ className, ...rest }: SVGProps<SVGSVGElement>) {
  return (
    <svg
      viewBox="0 0 1440 14"
      preserveAspectRatio="none"
      fill="currentColor"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <path d={`${WAVE_PATH} L 1440 14 L 0 14 Z`} />
    </svg>
  );
}

export function CornerSparkle({ size = 24, className, ...rest }: DoodleProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="currentColor"
      aria-hidden="true"
      className={className}
      {...rest}
    >
      <path d="M 26 4 L 27.6 10 L 33.6 12 L 27.6 14 L 26 20 L 24.4 14 L 18.4 12 L 24.4 10 Z" />
      <path fill="none" stroke="currentColor" strokeWidth={2} d="M 8 26 q -2 -2 0 -4" opacity="0.7" />
    </svg>
  );
}