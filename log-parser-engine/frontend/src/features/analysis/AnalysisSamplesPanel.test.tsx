import { render, screen } from "@testing-library/react";

import type { AnalysisEventSample } from "../../lib/api/types";
import { AnalysisSamplesPanel } from "./AnalysisSamplesPanel";

describe("AnalysisSamplesPanel", () => {
  it("shows a warning and caps rendered rows for oversized sample payloads", () => {
    const samples = Array.from({ length: 130 }, (_, index) => sample(index + 1));

    render(<AnalysisSamplesPanel samples={samples} />);

    expect(screen.getByText(/Görünüm sınırı aktif/)).toBeInTheDocument();
    expect(screen.getByText("100 örnek event gösteriliyor.")).toBeInTheDocument();
    expect(screen.getAllByText("service-1").length).toBeGreaterThan(0);
    expect(screen.queryByText("service-130")).not.toBeInTheDocument();
  });

  it("renders empty state when samples are not included", () => {
    render(<AnalysisSamplesPanel samples={[]} />);

    expect(
      screen.getByText("İstekte örnek event üretimi kapalı veya sonuç boş.")
    ).toBeInTheDocument();
  });
});

function sample(index: number): AnalysisEventSample {
  return {
    event_id: `event-${index}`,
    timestamp: "2026-08-03T12:00:00Z",
    severity: "info",
    source_type: "application",
    message_preview: `sample-${index}`,
    event_type: `service-${index}`,
    service: `service-${index}`,
    host: "host-1",
    parser_name: "json"
  };
}
