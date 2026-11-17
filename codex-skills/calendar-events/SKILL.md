---
name: calendar-events
description: Create or update Google Calendar events with verified locations and usable Google Maps links. Use for adding, moving, correcting, or annotating calendar events; not for broader daily or weekly time-block planning or phone alarms.
---

# Calendar Events

Use the connected Google Calendar tools. Search within an explicit time window and read the exact event before changing an existing one. Preserve unrelated event details and verify the saved result by reading it back.

## Locations and map links

Whenever creating or materially updating an event with an in-person location:

- Put the room or meeting point and the full venue address in the Calendar location field when they are known.
- Include a clickable Google Maps URL in the event description, even when Calendar can already map the location field. Use `https://www.google.com/maps/search/?api=1&query=<URL-encoded venue and address>`.
- Preserve an existing Maps link and do not add a duplicate. Replace a stale or incorrect link when correcting the location.
- Preserve remote-meeting links. Remote-only events do not need a Maps link.

If the supplied location is incomplete or ambiguous, first resolve it from an authoritative source such as the institution, venue, organizer, or official directory. Preserve useful room, entrance, building, or campus details that Maps alone cannot represent. If the location is still uncertain, do not invent an address or misleading link: retain the known details, mark the location as needing confirmation in the description when appropriate, and tell the user exactly what remains unresolved.

For a Maps-only enrichment that does not change the actual venue or time, do not notify guests. Follow the Calendar tool's notification guidance for substantive changes that attendees need to know about.
