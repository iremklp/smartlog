import "@testing-library/jest-dom";

class ResizeObserverMock implements ResizeObserver {
  readonly #callback: ResizeObserverCallback;

  constructor(callback: ResizeObserverCallback) {
    this.#callback = callback;
  }

  observe(target: Element): void {
    this.#callback(
      [
        {
          target,
          contentRect: new DOMRect(0, 0, 1024, 400)
        } as ResizeObserverEntry
      ],
      this
    );
  }

  unobserve(): void {}

  disconnect(): void {}
}

globalThis.ResizeObserver = ResizeObserverMock;
