import type { EventPage, LogEvent } from "./types";

/**
 * Derives forward-pagination state from fields serialized by the backend.
 *
 * When the total count was intentionally omitted, a full page means that
 * another page may exist. A short page is terminal.
 */
export function eventPageHasMore(page: EventPage): boolean {
  if (page.total !== null) {
    return page.offset + page.returned < page.total;
  }
  return page.returned > 0 && page.returned === page.limit;
}

export function getNextEventOffset(page: EventPage): number | null {
  return eventPageHasMore(page) ? page.offset + page.returned : null;
}

/** Reads normalized parser metadata without assuming a non-canonical field. */
export function getEventParserName(event: Pick<LogEvent, "attributes">): string | null {
  const parserName = event.attributes.parser_name;
  if (typeof parserName !== "string") {
    return null;
  }
  const normalized = parserName.trim();
  return normalized || null;
}
