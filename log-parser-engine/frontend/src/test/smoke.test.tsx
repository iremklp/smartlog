import { render, screen } from "@testing-library/react";
import { RouterProvider, createMemoryRouter } from "react-router-dom";

import { AppProviders } from "../app/providers";
import { AnalysisPage } from "../pages/AnalysisPage";

describe("frontend smoke", () => {
  it("renders analysis page", async () => {
    const router = createMemoryRouter([
      {
        path: "/",
        element: <AnalysisPage />
      }
    ]);

    render(
      <AppProviders>
        <RouterProvider router={router} />
      </AppProviders>
    );

    expect(await screen.findByText("Log Analysis")).toBeInTheDocument();
  });
});
