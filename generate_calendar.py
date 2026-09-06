import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"
OUTPUT = Path("docs/pannal-ash-flames.ics")

FLAMES = "Pannal Ash JFC U14 Girls Flames"

URL = "https://r.jina.ai/" + TEAM_URL

print("=" * 60)
print("PANNAL ASH FLAMES CALENDAR")
print("=" * 60)

# ------------------------------------------------------------
# Download the FA Full-Time page
# ------------------------------------------------------------

response = requests.get(
    URL,
    timeout=60,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

response.raise_for_status()

text = response.text

print("FA page downloaded successfully")
print("Characters downloaded:", len(text))


# ------------------------------------------------------------
# Find fixture sections
#
# Each fixture starts with:
#
# | L | 12/09/26 10:00 |
#
# followed by the home and away team links.
# ------------------------------------------------------------

fixture_pattern = re.compile(
    r"\|\s*[A-Z]\s*\|\s*"
    r"(\d{2}/\d{2}/\d{2,4})\s+(\d{1,2}:\d{2})\s*\|"
    r"(.*?)(?=\|\s*[A-Z]\s*\|\s*\d{2}/\d{2}/\d{2,4}\s+\d{1,2}:\d{2}\s*\||\Z)",
    re.DOTALL
)

fixtures = []

for match in fixture_pattern.finditer(text):

    date_text = match.group(1)
    time_text = match.group(2)
    block = match.group(3)

    # Find all normal Markdown links in this fixture.
    # The first two are the home and away teams.
    team_links = re.findall(
        r"\[([^\]]+)\]\(\s*(https://fulltime\.thefa\.com/displayFixture\.html\?id=\d+)\s*\)",
        block
    )

    if len(team_links) < 2:
        continue

    home = team_links[0][0].strip()
    fixture_url = team_links[0][1].strip()

    away = team_links[1][0].strip()

    # We only want fixtures involving the FLAMES.
    #
    # This deliberately excludes:
    # Pannal Ash JFC U14 Girls Flashes v Other Team
    #
    # But includes:
    # Pannal Ash JFC U14 Girls Flashes v Pannal Ash JFC U14 Girls Flames

    if home != FLAMES and away != FLAMES:
        continue

    fixtures.append({
        "date": date_text,
        "time": time_text,
        "home": home,
        "away": away,
        "url": fixture_url,
    })


# Remove duplicates using fixture URL
unique = {}

for fixture in fixtures:
    unique[fixture["url"]] = fixture

fixtures = list(unique.values())


# ------------------------------------------------------------
# Sort fixtures chronologically
# ------------------------------------------------------------

def sort_key(fixture):
    for fmt in ("%d/%m/%y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(
                f"{fixture['date']} {fixture['time']}",
                fmt
            )
        except ValueError:
            pass

    return datetime.max


fixtures.sort(key=sort_key)


print()
print("=" * 60)
print("FLAMES FIXTURES FOUND:", len(fixtures))
print("=" * 60)

for fixture in fixtures:
    print(
        fixture["date"],
        fixture["time"],
        "-",
        fixture["home"],
        "v",
        fixture["away"]
    )


# ------------------------------------------------------------
# iCalendar helpers
# ------------------------------------------------------------

def ics_escape(value):
    """Escape text for an iCalendar field."""
    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r", "")
        .replace("\n", "\\n")
    )


# ------------------------------------------------------------
# Build the calendar
# ------------------------------------------------------------

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Pannal Ash JFC//U14 Girls Flames//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Pannal Ash U14 Girls Flames",
    "X-WR-CALDESC:Pannal Ash U14 Girls Flames fixtures",
    "X-WR-TIMEZONE:Europe/London",
]

now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


for fixture in fixtures:

    dt = sort_key(fixture)

    # Assume a 90-minute fixture.
    end = dt + timedelta(minutes=90)

    # Use a stable UID based on the FA fixture ID.
    fixture_id_match = re.search(
        r"id=(\d+)",
        fixture["url"]
    )

    if fixture_id_match:
        fixture_id = fixture_id_match.group(1)
    else:
        fixture_id = re.sub(r"\W+", "", fixture["url"])

    uid = f"{fixture_id}@pannal-ash-flames-calendar"

    summary = f"{fixture['home']} v {fixture['away']}"

    description = (
        f"FA Full-Time fixture: {fixture['home']} v {fixture['away']}\\n"
        f"{fixture['url']}"
    )

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(description)}",
        f"URL:{fixture['url']}",
        "END:VEVENT",
    ])


lines.append("END:VCALENDAR")


# ------------------------------------------------------------
# Write the calendar
# ------------------------------------------------------------

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

OUTPUT.write_text(
    "\r\n".join(lines) + "\r\n",
    encoding="utf-8"
)

print()
print("=" * 60)
print("CALENDAR CREATED")
print("=" * 60)
print("Events written:", len(fixtures))
print("File:", OUTPUT)
print("File size:", OUTPUT.stat().st_size, "bytes")
