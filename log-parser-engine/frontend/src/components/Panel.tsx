import type { PropsWithChildren, ReactNode } from "react";

interface PanelProps extends PropsWithChildren {
  title: string;
  subtitle?: string;
  rightSlot?: ReactNode;
}

export function Panel({ title, subtitle, rightSlot, children }: PanelProps) {
  return (
    <section className="rounded-2xl border border-white/10 bg-panel/90 p-5 shadow-panel backdrop-blur animate-rise">
      <header className="mb-4 flex items-start justify-between gap-4">
        <div>
          <h2 className="font-display text-lg font-semibold tracking-wide text-ink">{title}</h2>
          {subtitle ? <p className="mt-1 text-sm text-inkSoft">{subtitle}</p> : null}
        </div>
        {rightSlot}
      </header>
      {children}
    </section>
  );
}
