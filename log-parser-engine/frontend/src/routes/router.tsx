import { createBrowserRouter } from "react-router-dom";

import { NavShell } from "../components/NavShell";
import { AnalysisPage } from "../pages/AnalysisPage";
import { DashboardPage } from "../pages/DashboardPage";
import { EventDetailPage } from "../pages/EventDetailPage";
import { EventsPage } from "../pages/EventsPage";
import { NotFoundPage } from "../pages/NotFoundPage";
import { ParsersPage } from "../pages/ParsersPage";
import { StorePage } from "../pages/StorePage";
import { SystemPage } from "../pages/SystemPage";

export const router = createBrowserRouter([
  {
    path: "/",
    element: <NavShell />,
    errorElement: <NotFoundPage />,
    children: [
      { index: true, element: <AnalysisPage /> },
      { path: "analysis", element: <AnalysisPage /> },
      { path: "events", element: <EventsPage /> },
      { path: "events/:eventId", element: <EventDetailPage /> },
      { path: "dashboard", element: <DashboardPage /> },
      { path: "parsers", element: <ParsersPage /> },
      { path: "store", element: <StorePage /> },
      { path: "system", element: <SystemPage /> },
      { path: "*", element: <NotFoundPage /> }
    ]
  }
]);
