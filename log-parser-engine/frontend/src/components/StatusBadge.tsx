interface StatusBadgeProps {
  label: string;
  tone?: "ok" | "warn" | "err" | "info";
}

const toneClassMap: Record<NonNullable<StatusBadgeProps["tone"]>, string> = {
  ok: "bg-ok/20 text-ok border-ok/40",
  warn: "bg-warn/20 text-warn border-warn/40",
  err: "bg-err/20 text-err border-err/40",
  info: "bg-accent/20 text-accent border-accent/40"
};

export function StatusBadge({ label, tone = "info" }: StatusBadgeProps) {
  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-1 text-xs font-semibold ${toneClassMap[tone]}`}>
      {label}
    </span>
  );
}
