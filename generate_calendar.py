import requests
from pathlib import Path
import re

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"

# Use Jina Reader to get the FA page through a proxy.
URL = "https://r.jina.ai/" + TEAM_URL

print("=" * 60)
print("PANNAL ASH U14 GIRLS FLAMES - FA PAGE DIAGNOSTIC")
print("=" * 60)
print()
print("Fetching FA Full-Time page...")
print(URL)
print()

try:
    response = requests.get(
        URL,
        timeout=60,
        headers={"User-Agent": "Mozilla/5.0"}
    )
    response.raise_for_status()
except Exception as e:
    print("ERROR:")
    print(e)
    raise

text = response.text

print("SUCCESS")
print(f"HTTP status: {response.status_code}")
print(f"Characters downloaded: {len(text)}")
print()

# ---------------------------------------------------------
# 1. Look for anything mentioning Pannal / Flames
# ---------------------------------------------------------

print("=" * 60)
print("LINES CONTAINING 'PANNAL' OR 'FLAMES'")
print("=" * 60)

found_team_lines = []

for line_number, line in enumerate(text.splitlines(), 1):
    clean = " ".join(line.split())

    if (
        "pannal" in clean.lower()
        or
        "flames" in clean.lower()
    ):
        found_team_lines.append((line_number, clean))

for line_number, clean in found_team_lines:
    print(f"{line_number}: {clean[:1000]}")

print()
print(f"Number of matching lines: {len(found_team_lines)}")
print()

# ---------------------------------------------------------
# 2. Look for dates
# ---------------------------------------------------------

print("=" * 60)
print("LINES CONTAINING DATES")
print("=" * 60)

date_lines = []

for line_number, line in enumerate(text.splitlines(), 1):
    clean = " ".join(line.split())

    if re.search(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b", clean):
        date_lines.append((line_number, clean))

for line_number, clean in date_lines[:100]:
    print(f"{line_number}: {clean[:1000]}")

print()
print(f"Number of lines containing dates: {len(date_lines)}")
print()

# ---------------------------------------------------------
# 3. Look for common football fixture terminology
# ---------------------------------------------------------

print("=" * 60)
print("LINES CONTAINING FIXTURE-RELATED WORDS")
print("=" * 60)

fixture_words = [
    "fixture",
    "fixtures",
    "home",
    "away",
    "kick off",
    "kickoff",
    "venue",
    "result",
    "match",
]

fixture_lines = []

for line_number, line in enumerate(text.splitlines(), 1):
    clean = " ".join(line.split())

    if any(word in clean.lower() for word in fixture_words):
        fixture_lines.append((line_number, clean))

for line_number, clean in fixture_lines[:150]:
    print(f"{line_number}: {clean[:1000]}")

print()
print(f"Number of fixture-related lines: {len(fixture_lines)}")
print()

# ---------------------------------------------------------
# 4. Look for "v" or "vs" matches
# ---------------------------------------------------------

print("=" * 60)
print("LINES CONTAINING ' V ' OR ' VS '")
print("=" * 60)

versus_lines = []

for line_number, line in enumerate(text.splitlines(), 1):
    clean = " ".join(line.split())

    if (
        re.search(r"\s+v\s+", clean, re.IGNORECASE)
        or
        re.search(r"\s+vs\.?\s+", clean, re.IGNORECASE)
    ):
        versus_lines.append((line_number, clean))

for line_number, clean in versus_lines[:150]:
    print(f"{line_number}: {clean[:1000]}")

print()
print(f"Number of v/vs lines: {len(versus_lines)}")
print()

# ---------------------------------------------------------
# 5. Print the first 200 lines of the actual response.
# ---------------------------------------------------------

print("=" * 60)
print("FIRST 200 LINES OF ACTUAL FA RESPONSE")
print("=" * 60)

all_lines = text.splitlines()

for number, line in enumerate(all_lines[:200], 1):
    clean = " ".join(line.split())

    if clean:
        print(f"{number}: {clean[:1000]}")

print()
print("=" * 60)
print("END OF DIAGNOSTIC")
print("=" * 60)
