import { ReactElement, Suspense } from "react";

export function LazyRoute({ element }: { element: ReactElement }) {
  return (
    <Suspense
      fallback={
        <div
          role="status"
          className="rounded-2xl border border-white/10 bg-panel/80 p-6 text-sm text-inkSoft"
        >
          Sayfa yükleniyor...
        </div>
      }
    >
      {element}
    </Suspense>
  );
}
