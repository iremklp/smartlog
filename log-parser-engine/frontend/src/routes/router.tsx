import { lazy } from "react";
import { createBrowserRouter } from "react-router-dom";

import { NavShell } from "../components/NavShell";
import { NotFoundPage } from "../pages/NotFoundPage";
import { LazyRoute } from "./LazyRoute";

const AnalysisPage = lazy(() =>
  import("../pages/AnalysisPage").then((module) => ({ default: module.AnalysisPage }))
);
const StatisticalAnalysisPage = lazy(() =>
  import("../pages/StatisticalAnalysisPage").then((module) => ({
    default: module.StatisticalAnalysisPage
  }))
);
const ComparisonAnalysisPage = lazy(() =>
  import("../pages/ComparisonAnalysisPage").then((module) => ({
    default: module.ComparisonAnalysisPage
  }))
);
const EventsPage = lazy(() =>
  import("../pages/EventsPage").then((module) => ({ default: module.EventsPage }))
);
const EventDetailPage = lazy(() =>
  import("../pages/EventDetailPage").then((module) => ({ default: module.EventDetailPage }))
);
const DashboardPage = lazy(() =>
  import("../pages/DashboardPage").then((module) => ({ default: module.DashboardPage }))
);
const ParsersPage = lazy(() =>
  import("../pages/ParsersPage").then((module) => ({ default: module.ParsersPage }))
);
const StorePage = lazy(() =>
  import("../pages/StorePage").then((module) => ({ default: module.StorePage }))
);
const SystemPage = lazy(() =>
  import("../pages/SystemPage").then((module) => ({ default: module.SystemPage }))
);

export const router = createBrowserRouter([
  {
    path: "/",
    element: <NavShell />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <LazyRoute element={<AnalysisPage />} /> },
      { path: "analysis", element: <LazyRoute element={<AnalysisPage />} /> },
      { path: "analytics", element: <LazyRoute element={<StatisticalAnalysisPage />} /> },
      {
        path: "analytics/compare",
        element: <LazyRoute element={<ComparisonAnalysisPage />} />
      },
      { path: "events", element: <LazyRoute element={<EventsPage />} /> },
      { path: "events/:eventId", element: <LazyRoute element={<EventDetailPage />} /> },
      { path: "dashboard", element: <LazyRoute element={<DashboardPage />} /> },
      { path: "parsers", element: <LazyRoute element={<ParsersPage />} /> },
      { path: "store", element: <LazyRoute element={<StorePage />} /> },
      { path: "system", element: <LazyRoute element={<SystemPage />} /> },
      { path: "*", element: <NotFoundPage /> }
    ]
  }
]);
