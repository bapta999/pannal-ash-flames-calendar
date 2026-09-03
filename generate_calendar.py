import requests
from bs4 import BeautifulSoup
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
    print(f"ERROR fetching FA Full-Time page:")
    print(e)
    raise

text = response.text

print(f"HTTP status: {response.status_code}")
print(f"Downloaded characters: {len(text)}")
print()

# Save a copy of the downloaded page so we can inspect it if necessary.
debug_file = Path("docs/fa-debug.txt")
debug_file.write_text(text, encoding="utf-8")

print(f"Saved downloaded FA page to: {debug_file}")
print()

# ---------------------------------------------------------
# Try to find fixture-looking lines.
# ---------------------------------------------------------

# First look for lines containing a date and a v.
lines_with_fixtures = []

for line in text.splitlines():
    line = " ".join(line.split())

    if re.search(r"\d{2}/\d{2}/\d{2}", line) and re.search(r"\bv\b", line, re.IGNORECASE):
        lines_with_fixtures.append(line)

print(f"Potential fixture lines found: {len(lines_with_fixtures)}")

for line in lines_with_fixtures[:20]:
    print("  ", line)

print()

# ---------------------------------------------------------
# Extract fixtures.
#
# We deliberately don't restrict the venue to a fixed list.
# The previous version did, which could easily result in
# zero matches if FA Full-Time changes the wording.
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

    # Only keep fixtures involving the Flames team.
    if (
        "Pannal Ash JFC U14 Girls Flames" not in home
        and
        "Pannal Ash JFC U14 Girls Flames" not in away
    ):
        continue

    summary = f"{home} v {away}"

    events.append((dt, summary))

# Remove duplicates and sort.
events = list(dict.fromkeys(events))
events.sort()

print(f"Flames fixtures identified: {len(events)}")
print()

for dt, summary in events:
    print(f"  {dt.strftime('%d/%m/%Y %H:%M')} - {summary}")

print()

# ---------------------------------------------------------
# Create calendar
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

    # Stable UID based on fixture details.
    uid_source = f"{dt.isoformat()}|{summary}"
    uid_hash = hashlib.sha256(
        uid_source.encode("utf-8")
    ).hexdigest()[:16]

    uid = f"{uid_hash}@pannal-ash-flames"

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
        f"DTSTART;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{summary}",
        "DESCRIPTION:Pannal Ash JFC U14 Girls Flames fixture",
        "END:VEVENT",
    ])

lines.append("END:VCALENDAR")

# THIS WAS MISSING FROM THE PREVIOUS VERSION.
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
    print("The file docs/fa-debug.txt contains the page returned")
    print("by FA Full-Time so we can inspect its actual format.")
else:
    print("SUCCESS: Fixtures have been added to the calendar.")
