import { render, screen } from "@testing-library/react";

import type { DistributionResult } from "../../lib/api/types";
import { DistributionPanels } from "./DistributionPanels";

describe("DistributionPanels", () => {
  it("shows truncation warning and hidden-category footer when response is bounded", () => {
    render(
      <DistributionPanels
        distributions={[
          {
            field: "service",
            total_count: 120,
            matched_value_count: 120,
            missing_count: 0,
            unique_value_count: 25,
            items: Array.from({ length: 25 }, (_, index) => distributionItem(index + 1)),
            other_count: 40,
            truncated: true
          }
        ]}
      />
    );

    expect(screen.getByText(/Görünüm sınırı aktif/)).toBeInTheDocument();

    expect(screen.getByText("Service dağılım tablosu")).toBeInTheDocument();

    expect(screen.getByText(/kategori görünüm sınırı nedeniyle gizlendi/)).toBeInTheDocument();
    expect(screen.getByRole("rowheader", { name: "Service 1" })).toBeInTheDocument();
    expect(screen.queryByRole("rowheader", { name: "Service 25" })).not.toBeInTheDocument();
  });

  it("shows explicit empty row when distribution has no items", () => {
    const emptyDistribution: DistributionResult = {
      field: "service",
      total_count: 0,
      matched_value_count: 0,
      missing_count: 0,
      unique_value_count: 0,
      items: [],
      other_count: 0,
      truncated: false
    };

    render(<DistributionPanels distributions={[emptyDistribution]} />);

    expect(screen.getByText("Bu boyut için değer bulunamadı.")).toBeInTheDocument();
    expect(screen.getByText("Bu boyut için dağılım satırı bulunamadı.")).toBeInTheDocument();
  });
});

function distributionItem(rank: number) {
  return {
    rank,
    key: `service-${rank}`,
    display_value: `Service ${rank}`,
    count: 3,
    percentage: 2.5,
    metric_value: null,
    metric_unit: null,
    attributes: {}
  };
}
