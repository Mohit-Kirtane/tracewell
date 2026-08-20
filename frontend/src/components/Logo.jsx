export function Logo() {
  return (
    <span className="flex items-center gap-2.5 font-display text-[15px] font-semibold tracking-tight text-text">
      <span className="flex h-3 w-3.5 items-end gap-[2px]" aria-hidden="true">
        <span className="signal-bar h-full w-[3px] rounded-full bg-signal" style={{ animationDelay: "0s" }} />
        <span className="signal-bar h-full w-[3px] rounded-full bg-signal" style={{ animationDelay: "0.25s" }} />
        <span className="signal-bar h-full w-[3px] rounded-full bg-signal" style={{ animationDelay: "0.5s" }} />
      </span>
      tracewell
    </span>
  );
}
