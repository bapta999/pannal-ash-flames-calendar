import re
import requests
from pathlib import Path

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"
OUTPUT = Path("docs/pannal-ash-flames.ics")

URL = "https://r.jina.ai/" + TEAM_URL

print("=" * 60)
print("DOWNLOADING FA PAGE")
print("=" * 60)

response = requests.get(URL, timeout=60)

print("HTTP status:", response.status_code)
print("Downloaded characters:", len(response.text))

text = response.text

print()
print("=" * 60)
print("SEARCHING FOR IMPORTANT TERMS")
print("=" * 60)

for term in ["Pannal", "Flames", "fixture", "Killinghall", "Horsforth", "Wigton"]:
    matches = [line.strip() for line in text.splitlines()
               if term.lower() in line.lower()]

    print()
    print(f"TERM: {term}")
    print(f"MATCHES: {len(matches)}")

    for line in matches[:10]:
        print(line[:1500])

print()
print("=" * 60)
print("LINES CONTAINING DATES OR TIMES")
print("=" * 60)

for number, line in enumerate(text.splitlines(), 1):
    clean = " ".join(line.split())

    if (
        re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", clean)
        or re.search(r"\b\d{1,2}:\d{2}\b", clean)
    ):
        print(f"{number}: {clean[:1500]}")

print()
print("=" * 60)
print("FIRST 50 NON-EMPTY LINES")
print("=" * 60)

count = 0

for number, line in enumerate(text.splitlines(), 1):
    clean = " ".join(line.split())

    if clean:
        print(f"{number}: {clean[:1500]}")
        count += 1

        if count >= 50:
            break

print()
print("=" * 60)
print("END OF DIAGNOSTIC")
print("=" * 60)

# Create a basic empty calendar so the workflow still completes.

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

calendar = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Pannal Ash JFC//U14 Girls Flames//EN
CALSCALE:GREGORIAN
METHOD:PUBLISH
X-WR-CALNAME:Pannal Ash U14 Girls Flames
END:VCALENDAR
"""

OUTPUT.write_text(calendar, encoding="utf-8")

print("Empty calendar written to:", OUTPUT)
