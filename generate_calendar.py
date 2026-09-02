import requests
from bs4 import BeautifulSoup
from datetime import datetime
from pathlib import Path
import re

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"
OUTPUT = Path("docs/pannal-ash-flames.ics")

# Use Jina Reader as a proxy because FA Full-Time blocks GitHub's IP addresses.
URL = "https://r.jina.ai/" + TEAM_URL

response = requests.get(URL, timeout=60)
response.raise_for_status()

text = response.text

# Extract fixture rows from the Full-Time page.
pattern = re.compile(
    r"(\d{2}/\d{2}/\d{2})\s+(\d{2}:\d{2})\s+"
    r"(.+?)\s+v\s+(.+?)\s+"
    r"(?:KILLINGHALL|ALMSFORD|WIGTON|CLIFFORD|SCOTTON|PANNAL|BRAMHOPE|ILKLEY|HORsFORTH)",
    re.IGNORECASE
)

matches = pattern.findall(text)

events = []

for date, time, home, away in matches:
    try:
        dt = datetime.strptime(
            f"{date} {time}",
            "%d/%m/%y %H:%M"
        )
    except ValueError:
        continue

    # Only keep fixtures involving Flames.
    if "Pannal Ash JFC U14 Girls Flames" not in home and \
       "Pannal Ash JFC U14 Girls Flames" not in away:
        continue

    summary = f"{home.strip()} v {away.strip()}"

    events.append(
        (dt, summary)
    )

# Remove duplicates.
events = list(dict.fromkeys(events))
events.sort()

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

lines = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//Pannal Ash JFC//U14 Girls Flames//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:Pannal Ash U14 Girls Flames",
]

for dt, summary in events:
    uid = f"{dt.strftime('%Y%m%d%H%M')}-{abs(hash(summary))}@pannal-ash-flames"

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

OUTPUT.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")

print(f"Created {OUTPUT} with {len(events)} fixtures.")
