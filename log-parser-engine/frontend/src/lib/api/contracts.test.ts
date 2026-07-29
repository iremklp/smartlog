import { eventPageHasMore, getEventParserName, getNextEventOffset } from "./contracts";
import type { EventPage } from "./types";

describe("event API contract helpers", () => {
  it("uses the serialized total to derive a known next page", () => {
    const page: EventPage = {
      offset: 20,
      limit: 10,
      returned: 10,
      total: 31
    };

    expect(eventPageHasMore(page)).toBe(true);
    expect(getNextEventOffset(page)).toBe(30);
  });

  it("treats a short page with an omitted total as terminal", () => {
    const page: EventPage = {
      offset: 20,
      limit: 10,
      returned: 4,
      total: null
    };

    expect(eventPageHasMore(page)).toBe(false);
    expect(getNextEventOffset(page)).toBeNull();
  });

  it("treats a full page with an omitted total as potentially non-terminal", () => {
    const page: EventPage = {
      offset: 0,
      limit: 10,
      returned: 10,
      total: null
    };

    expect(eventPageHasMore(page)).toBe(true);
    expect(getNextEventOffset(page)).toBe(10);
  });

  it("reads parser identity only from a canonical string attribute", () => {
    expect(getEventParserName({ attributes: { parser_name: " json " } })).toBe("json");
    expect(getEventParserName({ attributes: { parser_name: 42 } })).toBeNull();
    expect(getEventParserName({ attributes: {} })).toBeNull();
  });
});
