interface JsonViewProps {
  value: unknown;
}

export function JsonView({ value }: JsonViewProps) {
  return (
    <pre className="max-h-[420px] overflow-auto rounded-xl border border-white/10 bg-black/30 p-3 font-mono text-xs text-emerald-100">
      {JSON.stringify(value, null, 2)}
    </pre>
  );
}
