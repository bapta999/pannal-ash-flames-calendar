import requests
from datetime import datetime, timezone
from pathlib import Path
import re
import hashlib
import html

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"
URL = "https://r.jina.ai/" + TEAM_URL

OUTPUT = Path("docs/pannal-ash-flames.ics")

TEAM_NAME = "Pannal Ash U14 Girls Flames"

print("=" * 60)
print("PANNAL ASH U14 GIRLS FLAMES CALENDAR")
print("=" * 60)
print()
print("Fetching FA Full-Time...")
print()

# ---------------------------------------------------------
# Download the FA Full-Time page through Jina
# ---------------------------------------------------------

response = requests.get(
    URL,
    timeout=60,
    headers={"User-Agent": "Mozilla/5.0"}
)

response.raise_for_status()

text = response.text

print(f"HTTP status: {response.status_code}")
print(f"Downloaded characters: {len(text)}")
print()

# ---------------------------------------------------------
# Clean up the downloaded Markdown/HTML
# ---------------------------------------------------------

text = html.unescape(text)

# Remove HTML tags where possible.
clean_text = re.sub(r"<[^>]+>", " ", text)

# ---------------------------------------------------------
# Find Markdown table rows.
#
# The FA page returned by Jina contains rows similar to:
#
# | L | 12/09/26 10:00 | [Home Team] | VS | [Away Team] | Venue |
#
# We process each table row separately.
# ---------------------------------------------------------

events = []

for raw_line in text.splitlines():

    line = raw_line.strip()

    # Only examine Markdown table rows.
    if not line.startswith("|"):
        continue

    # We need a date and time in the row.
    date_match = re.search(
        r"(\d{1,2}/\d{1,2}/\d{2,4})\s+(\d{1,2}:\d{2})",
        line
    )

    if not date_match:
        continue

    date_string = date_match.group(1)
    time_string = date_match.group(2)

    # -----------------------------------------------------
    # Extract all Markdown link text from the row.
    # -----------------------------------------------------

    links = re.findall(
        r"\[([^\]]+)\]\([^)]+\)",
        line
    )

    # Remove unnecessary whitespace.
    links = [
        " ".join(link.split()).strip()
        for link in links
    ]

    # -----------------------------------------------------
    # We are specifically interested in the two team names.
    #
    # Find the Flames team and use the link immediately
    # before/after it as the opponent.
    # -----------------------------------------------------

    flames_index = None

    for i, link in enumerate(links):
        if TEAM_NAME.lower() in link.lower():
            flames_index = i
            break

    if flames_index is None:
        continue

    # We need another team in the row.
    if len(links) < 2:
        continue

    # Usually the two team names are adjacent links.
    # Find the nearest other team name.
    opponent = None

    for i, link in enumerate(links):

        if i == flames_index:
            continue

        # Ignore obvious navigation/non-team links.
        if not link:
            continue

        opponent = link
        break

    if opponent is None:
        continue

    # -----------------------------------------------------
    # Determine home and away from the order in the table.
    # -----------------------------------------------------

    team_links = [
        link for link in links
        if link
    ]

    # Remove duplicates while preserving order.
    team_links = list(dict.fromkeys(team_links))

    if TEAM_NAME not in team_links:
        # Case-insensitive fallback.
        for i, link in enumerate(team_links):
            if link.lower() == TEAM_NAME.lower():
                team_links[i] = TEAM_NAME

    # Find Flames again after normalisation.
    try:
        flames_position = next(
            i for i, link in enumerate(team_links)
            if link.lower() == TEAM_NAME.lower()
        )
    except StopIteration:
        continue

    if len(team_links) < 2:
        continue

    # The first two relevant team links are the fixture teams.
    home = team_links[0]
    away = team_links[1]

    # -----------------------------------------------------
    # Make sure Flames is actually one of the two teams.
    # -----------------------------------------------------

    if (
        TEAM_NAME.lower() not in home.lower()
        and
        TEAM_NAME.lower() not in away.lower()
    ):
        continue

    # -----------------------------------------------------
    # Parse date/time.
    # -----------------------------------------------------

    parsed = None

    for date_format in ("%d/%m/%y %H:%M", "%d/%m/%Y %H:%M"):

        try:
            parsed = datetime.strptime(
                f"{date_string} {time_string}",
                date_format
            )
            break
        except ValueError:
            pass

    if parsed is None:
        continue

    # -----------------------------------------------------
    # Extract venue from the remaining table cells.
    # -----------------------------------------------------

    cells = [
        " ".join(cell.split()).strip()
        for cell in line.split("|")
    ]

    venue = ""

    # Look for a likely venue after the team information.
    for cell in cells:

        if not cell:
            continue

        lower = cell.lower()

        # Ignore cells containing teams or VS.
        if (
            "pannal ash" in lower
            or "girls" in lower
            or lower in ("vs", "v", "l", "w", "d")
        ):
            continue

        # Ignore Markdown links that are clearly team links.
        if "[" in cell and "](" in cell:
            continue

        # Keep a plausible venue.
        if len(cell) > 2:
            venue = re.sub(r"\[|\]", "", cell)
            break

    # -----------------------------------------------------
    # Create event.
    # -----------------------------------------------------

    summary = f"{home} v {away}"

    if venue:
        description = (
            f"Pannal Ash JFC U14 Girls Flames fixture. "
            f"Venue: {venue}"
        )
    else:
        description = (
            "Pannal Ash JFC U14 Girls Flames fixture"
        )

    events.append(
        {
            "datetime": parsed,
            "summary": summary,
            "description": description,
            "venue": venue,
        }
    )

# ---------------------------------------------------------
# Remove duplicate fixtures.
# ---------------------------------------------------------

unique_events = {}

for event in events:

    key = (
        event["datetime"],
        event["summary"]
    )

    unique_events[key] = event

events = list(unique_events.values())

events.sort(key=lambda event: event["datetime"])

# ---------------------------------------------------------
# Display what we found.
# ---------------------------------------------------------

print("=" * 60)
print(f"FLAMES FIXTURES FOUND: {len(events)}")
print("=" * 60)
print()

for event in events:

    print(
        f"{event['datetime'].strftime('%d/%m/%Y %H:%M')} "
        f"- {event['summary']}"
    )

    if event["venue"]:
        print(f"  Venue: {event['venue']}")

print()

# ---------------------------------------------------------
# iCalendar escaping
# ---------------------------------------------------------

def ical_escape(value):
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )

# ---------------------------------------------------------
# Build calendar
# ---------------------------------------------------------

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Pannal Ash JFC//U14 Girls Flames//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Pannal Ash U14 Girls Flames",
    "X-WR-TIMEZONE:Europe/London",
]

for event in events:

    dt = event["datetime"]

    # Create a stable UID based on the fixture.
    uid_source = (
        f"{dt.isoformat()}|"
        f"{event['summary']}"
    )

    uid_hash = hashlib.sha256(
        uid_source.encode("utf-8")
    ).hexdigest()[:20]

    uid = f"{uid_hash}@pannal-ash-flames"

    # For now use a 90-minute calendar event.
    # We can change this later if you want.
    end_dt = dt.replace(
        minute=dt.minute + 90
    )

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{end_dt.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ical_escape(event['summary'])}",
        f"DESCRIPTION:{ical_escape(event['description'])}",
    ])

    if event["venue"]:
        lines.append(
            f"LOCATION:{ical_escape(event['venue'])}"
        )

    lines.extend([
        "END:VEVENT"
    ])

lines.append("END:VCALENDAR")

# ---------------------------------------------------------
# Write the ICS file
# ---------------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT.write_text(
    "\r\n".join(lines) + "\r\n",
    encoding="utf-8"
)

print("=" * 60)
print("CALENDAR GENERATED")
print("=" * 60)
print()
print(f"Events written: {len(events)}")
print(f"File: {OUTPUT}")
print(f"File size: {OUTPUT.stat().st_size} bytes")
print()

if events:
    print("SUCCESS - fixtures have been added to the calendar.")
else:
    print("WARNING - ZERO FLAMES FIXTURES FOUND.")
    print("The FA page was downloaded successfully,")
    print("but no matching Flames rows were detected.")
