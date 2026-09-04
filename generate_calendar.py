import requests
from datetime import datetime
from pathlib import Path
import re
import hashlib

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"
OUTPUT = Path("docs/pannal-ash-flames.ics")

# FA Full-Time can block GitHub's IP addresses,
# so use Jina Reader as a proxy.
URL = "https://r.jina.ai/" + TEAM_URL

print("========================================")
print("Pannal Ash U14 Girls Flames Calendar")
print("========================================")
print(f"Fetching: {TEAM_URL}")
print()

# ---------------------------------------------------------
# Download the FA Full-Time page
# ---------------------------------------------------------

try:
    response = requests.get(
        URL,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )
    response.raise_for_status()
except Exception as e:
    print("ERROR fetching FA Full-Time page:")
    print(e)
    raise

text = response.text

print(f"HTTP status: {response.status_code}")
print(f"Downloaded characters: {len(text)}")
print()

# ---------------------------------------------------------
# Show anything containing "Pannal Ash"
# This helps us see exactly how FA Full-Time is returning
# the team information.
# ---------------------------------------------------------

print("Searching downloaded page for Pannal Ash...")
print("----------------------------------------")

pannal_lines = []

for line in text.splitlines():
    if "pannal" in line.lower():
        clean_line = " ".join(line.split())
        pannal_lines.append(clean_line)
        print(clean_line[:500])

print("----------------------------------------")
print(f"Lines containing Pannal: {len(pannal_lines)}")
print()

# Save the complete downloaded page for debugging.
debug_file = Path("fa-debug.txt")
debug_file.write_text(text, encoding="utf-8")

print(f"Saved downloaded FA page to: {debug_file}")
print()

# ---------------------------------------------------------
# Look for lines that appear to contain fixtures.
# ---------------------------------------------------------

print("Looking for potential fixture lines...")
print("----------------------------------------")

lines_with_fixtures = []

for line in text.splitlines():
    clean_line = " ".join(line.split())

    if (
        re.search(r"\d{2}/\d{2}/\d{2}", clean_line)
        and
        re.search(r"\bv\b", clean_line, re.IGNORECASE)
    ):
        lines_with_fixtures.append(clean_line)
        print(clean_line[:500])

print("----------------------------------------")
print(f"Potential fixture lines found: {len(lines_with_fixtures)}")
print()

# ---------------------------------------------------------
# Extract fixtures.
#
# We deliberately do NOT restrict the venue to a fixed list.
# ---------------------------------------------------------

pattern = re.compile(
    r"(\d{2}/\d{2}/\d{2})\s+"
    r"(\d{1,2}:\d{2})\s+"
    r"(.+?)\s+"
    r"\bv\b\s+"
    r"(.+?)(?=\s+\d{2}/\d{2}/\d{2}|\s*$)",
    re.IGNORECASE
)

matches = pattern.findall(text)

print(f"Regex fixture matches: {len(matches)}")
print()

# ---------------------------------------------------------
# Turn matches into calendar events.
# ---------------------------------------------------------

events = []

for date, time, home, away in matches:

    home = " ".join(home.split()).strip()
    away = " ".join(away.split()).strip()

    try:
        dt = datetime.strptime(
            f"{date} {time}",
            "%d/%m/%y %H:%M"
        )
    except ValueError:
        continue

    # Only keep fixtures involving the Flames.
    if (
        "pannal ash jfc u14 girls flames" not in home.lower()
        and
        "pannal ash jfc u14 girls flames" not in away.lower()
    ):
        continue

    summary = f"{home} v {away}"

    events.append((dt, summary))

# Remove duplicates.
events = list(dict.fromkeys(events))

# Sort by date/time.
events.sort()

# ---------------------------------------------------------
# Display the fixtures we found.
# ---------------------------------------------------------

print("========================================")
print(f"Flames fixtures identified: {len(events)}")
print("========================================")

for dt, summary in events:
    print(
        f"{dt.strftime('%d/%m/%Y %H:%M')} - {summary}"
    )

print()

# ---------------------------------------------------------
# Create the calendar.
# ---------------------------------------------------------

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Pannal Ash JFC//U14 Girls Flames//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Pannal Ash U14 Girls Flames",
    "X-WR-TIMEZONE:Europe/London",
]

for dt, summary in events:

    # Create a stable UID for each fixture.
    uid_source = f"{dt.isoformat()}|{summary}"

    uid_hash = hashlib.sha256(
        uid_source.encode("utf-8")
    ).hexdigest()[:16]

    uid = f"{uid_hash}@pannal-ash-flames"

    # Escape characters that have special meaning in iCalendar.
    safe_summary = (
        summary
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{safe_summary}",
        "DESCRIPTION:Pannal Ash JFC U14 Girls Flames fixture",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

# ---------------------------------------------------------
# IMPORTANT:
# Actually write the calendar file.
# ---------------------------------------------------------

OUTPUT.write_text(
    "\r\n".join(lines) + "\r\n",
    encoding="utf-8"
)

print("========================================")
print("Calendar generated successfully")
print("========================================")
print(f"Events written: {len(events)}")
print(f"Output file: {OUTPUT}")
print(f"Output size: {OUTPUT.stat().st_size} bytes")
print()

if len(events) == 0:

    print("WARNING: ZERO FLAMES FIXTURES WERE FOUND.")
    print()
    print(
        "The downloaded FA page has been saved as "
        "fa-debug.txt."
    )
    print(
        "The Pannal Ash lines printed above will help "
        "us determine the correct format."
    )

else:

    print(
        "SUCCESS: Fixtures have been added to the calendar."
    )
