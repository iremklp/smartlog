import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ComparisonRequestForm } from "./ComparisonRequestForm";
import {
  DEFAULT_COMPARISON_REQUEST_STATE,
  buildComparisonRequest,
  type ComparisonRequestState
} from "./request-state";

describe("ComparisonRequestForm", () => {
  it("exposes labelled period, metric, group and rendering-bound controls", () => {
    renderForm();

    expect(screen.getByRole("group", { name: "Referans dönemi" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Karşılaştırma dönemi" })).toBeInTheDocument();
    expect(screen.getByLabelText("Referans başlangıcı")).toBeInTheDocument();
    expect(screen.getByLabelText("Karşılaştırma bitişi")).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Karşılaştırma metrikleri" })).toBeInTheDocument();
    expect(screen.getByRole("group", { name: "Grup boyutları" })).toBeInTheDocument();
    expect(screen.getByLabelText("Boyut başına Top N")).toHaveAttribute("max", "20");
  });

  it("applies an equal-window preset and submits timezone-aware wire values", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn<(values: ComparisonRequestState) => void>();
    renderForm({ onSubmit, getNow: () => new Date("2026-08-03T12:00:00.000Z") });

    await user.click(screen.getByRole("button", { name: "Preseti uygula" }));
    expect(screen.getByLabelText("Referans etiketi")).toHaveValue("Önceki 1 saat");
    expect(screen.getByLabelText("Karşılaştırma etiketi")).toHaveValue("Son 1 saat");

    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));

    const request = buildComparisonRequest(onSubmit.mock.calls[0]?.[0] as ComparisonRequestState);
    expect(request.baseline_filter).toEqual({
      start_time: "2026-08-03T10:00:00.000Z",
      end_time: "2026-08-03T11:00:00.000Z"
    });
    expect(request.comparison_filter).toEqual({
      start_time: "2026-08-03T11:00:00.000Z",
      end_time: "2026-08-03T12:00:00.000Z"
    });
  });

  it("blocks reversed periods and bounded values before submission", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn<(values: ComparisonRequestState) => void>();
    renderForm({ onSubmit });

    fireEvent.change(screen.getByLabelText("Referans başlangıcı"), {
      target: { value: "2026-08-03T12:00" }
    });
    fireEvent.change(screen.getByLabelText("Referans bitişi"), {
      target: { value: "2026-08-03T11:00" }
    });
    fireEvent.change(screen.getByLabelText("Boyut başına Top N"), {
      target: { value: "21" }
    });
    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));

    expect(
      await screen.findByText("Bitiş zamanı başlangıçtan sonra olmalıdır")
    ).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("shows a field error for every missing period boundary", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn<(values: ComparisonRequestState) => void>();
    renderForm({ onSubmit });

    for (const label of [
      "Referans başlangıcı",
      "Referans bitişi",
      "Karşılaştırma başlangıcı",
      "Karşılaştırma bitişi"
    ]) {
      fireEvent.change(screen.getByLabelText(label), { target: { value: "" } });
    }
    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));

    expect(await screen.findByText("Referans başlangıcı zorunludur")).toBeInTheDocument();
    expect(screen.getByText("Referans bitişi zorunludur")).toBeInTheDocument();
    expect(screen.getByText("Karşılaştırma başlangıcı zorunludur")).toBeInTheDocument();
    expect(screen.getByText("Karşılaştırma bitişi zorunludur")).toBeInTheDocument();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it("resets to a fresh last-hour window before the next comparison", async () => {
    const user = userEvent.setup();
    const onSubmit = vi.fn<(values: ComparisonRequestState) => void>();
    renderForm({ onSubmit, getNow: () => new Date("2026-08-03T12:00:00.000Z") });

    const baselineLabel = screen.getByLabelText("Referans etiketi");
    await user.clear(baselineLabel);
    await user.type(baselineLabel, "Özel referans");
    await user.click(screen.getByRole("button", { name: "Formu sıfırla" }));

    expect(baselineLabel).toHaveValue(DEFAULT_COMPARISON_REQUEST_STATE.baselineLabel);
    await user.click(screen.getByRole("button", { name: "Karşılaştırmayı uygula" }));
    await waitFor(() => expect(onSubmit).toHaveBeenCalledTimes(1));
    expect(
      buildComparisonRequest(onSubmit.mock.calls[0]?.[0] as ComparisonRequestState)
        .comparison_filter?.end_time
    ).toBe("2026-08-03T12:00:00.000Z");
  });
});

interface RenderFormOptions {
  onSubmit?: (values: ComparisonRequestState) => void;
  getNow?: () => Date;
}

function renderForm(options: RenderFormOptions = {}): void {
  render(
    <ComparisonRequestForm
      defaultValues={DEFAULT_COMPARISON_REQUEST_STATE}
      pending={false}
      onSubmit={options.onSubmit ?? vi.fn()}
      getNow={options.getNow}
    />
  );
}
