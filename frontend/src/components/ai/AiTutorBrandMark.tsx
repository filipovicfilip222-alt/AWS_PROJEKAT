/**
 * Premium brand mark for AI Tutor.
 * Used in both the desktop side panel header and the mobile bottom sheet.
 * Renders a circular violet → fuchsia gradient badge with a custom asterisk
 * glyph, plus a Fraunces serif title and a "Powered by Claude" subtitle.
 */
export function AiTutorBrandMark() {
  return (
    <div className="flex items-center gap-3">
      <div className="relative w-10 h-10 rounded-full bg-gradient-to-br from-violet-600 via-violet-500 to-fuchsia-500 flex items-center justify-center shadow-md ring-1 ring-violet-200/40">
        <svg
          viewBox="0 0 24 24"
          className="w-5 h-5 text-white"
          fill="currentColor"
          aria-hidden="true"
        >
          <path d="M12 2 L13.2 9.4 L20.5 8 L15.6 13.2 L20.5 18.4 L13.2 17 L12 24 L10.8 17 L3.5 18.4 L8.4 13.2 L3.5 8 L10.8 9.4 Z" />
        </svg>
      </div>
      <div className="flex flex-col">
        <h3
          className="font-display text-base text-slate-900 leading-tight tracking-tight"
          style={{ fontVariationSettings: '"opsz" 48, "SOFT" 30, "WONK" 0' }}
        >
          AI Tutor
        </h3>
        <span className="text-[10px] font-medium tracking-[0.16em] text-slate-400 uppercase mt-0.5">
          Powered by Claude
        </span>
      </div>
    </div>
  );
}
