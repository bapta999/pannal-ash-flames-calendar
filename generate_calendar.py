import requests
from datetime import datetime, timedelta

FA_URL = "https://fulltime.thefa.com/fixtures.html?selectedSeason=41815654&selectedFixtureGroupAgeGroup=0&selectedFixtureGroupKey=1_925809922&selectedDateCode=all&selectedClub=&selectedTeam=101016902&selectedRelatedFixtureOption=3&selectedFixtureDateStatus=&selectedFixtureStatus=&previousSelectedFixtureGroupAgeGroup=&previousSelectedFixtureGroupKey=1_925809922&previousSelectedClub=&itemsPerPage=25"

TEAM = "Pannal Ash JFC U14 Girls Flames"

# Get the FA Full-Time page
response = requests.get(
    FA_URL,
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30
)
response.raise_for_status()

html = response.text

# Save the page so the next step can inspect exactly what
# the FA currently returns.
with open("fa_page.html", "w", encoding="utf-8") as f:
    f.write(html)

print("FA Full-Time page downloaded successfully.")
print("Page size:", len(html), "characters")
print("Flames found:", TEAM in html)
