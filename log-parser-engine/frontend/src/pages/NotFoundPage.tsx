import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="grid min-h-[60vh] place-items-center rounded-2xl border border-white/10 bg-panel/80 p-8 text-center">
      <div>
        <h2 className="font-display text-3xl text-accent">Signal Lost</h2>
        <p className="mt-2 text-sm text-inkSoft">The route you requested does not exist in this control room.</p>
        <Link to="/analysis" className="mt-4 inline-block rounded-xl bg-accent px-4 py-2 font-semibold text-black">
          Back to Analysis
        </Link>
      </div>
    </div>
  );
}
