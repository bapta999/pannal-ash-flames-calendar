import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"

RESULTS_URL = (
    "https://fulltime.thefa.com/results.html"
    "?league=1867937"
    "&selectedSeason=41815654"
    "&selectedDivision=308032551"
    "&selectedCompetition=0"
    "&selectedFixtureGroupKey=1_925809922"
)

OUTPUT = Path("docs/pannal-ash-flames.ics")

FLAMES = "Pannal Ash JFC U14 Girls Flames"

TEAM_SOURCE_URL = "https://r.jina.ai/" + TEAM_URL
RESULTS_SOURCE_URL = "https://r.jina.ai/" + RESULTS_URL

print("=" * 60)
print("PANNAL ASH FLAMES CALENDAR")
print("=" * 60)


# ------------------------------------------------------------
# Download a page through Jina
# ------------------------------------------------------------

def download_page(url):
    response = requests.get(
        url,
        timeout=60,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    return response.text


# ------------------------------------------------------------
# Download the FA Full-Time team page
# ------------------------------------------------------------

text = download_page(TEAM_SOURCE_URL)

print("FA team page downloaded successfully")
print("Characters downloaded:", len(text))


# ------------------------------------------------------------
# Download the correct Flames results page
# ------------------------------------------------------------

results_text = download_page(RESULTS_SOURCE_URL)

print("FA results page downloaded successfully")
print("Result characters downloaded:", len(results_text))
print(results_text)


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean_name(name):
    """
    Clean a team name taken from Markdown or image alt text.
    """
    name = re.sub(r"!\[[^\]]*\]\([^)]+\)", "", name)
    name = re.sub(r"\[[^\]]+\]\([^)]+\)", "", name)

    name = name.replace("&nbsp;", " ")
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def normalise_team_name(name):
    """
    Normalise a team name for comparison without changing
    the actual name written into the calendar.
    """
    name = clean_name(name)

    name = name.replace("’", "'")
    name = name.replace("–", "-")
    name = name.replace("—", "-")

    return re.sub(r"\s+", " ", name).strip().lower()


def is_flames(name):
    return normalise_team_name(name) == normalise_team_name(FLAMES)


def parse_date_time(date_text, time_text):
    for fmt in (
        "%d/%m/%y %H:%M",
        "%d/%m/%Y %H:%M",
    ):
        try:
            return datetime.strptime(
                f"{date_text} {time_text}",
                fmt
            )
        except ValueError:
            pass

    return None


# ------------------------------------------------------------
# Find future fixtures
#
# Each fixture starts with:
#
# | L | 19/09/26 11:30 |
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

    # Find normal Markdown links.
    team_links = re.findall(
        r"\[([^\]]+)\]\(\s*(https://fulltime\.thefa\.com/"
        r"display(?:Fixture|CountyFixture)\.html\?id=\d+[^)]*)\s*\)",
        block
    )

    if len(team_links) < 2:
        continue

    home = clean_name(team_links[0][0])
    fixture_url = team_links[0][1].strip()

    away = clean_name(team_links[1][0])

    # Only include fixtures involving Flames.
    #
    # This excludes fixtures involving Flashes alone,
    # but correctly includes Flames v Flashes.

    if not is_flames(home) and not is_flames(away):
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
# Find completed results
#
# The results page uses rows containing:
#
# | L | 12/09/26 10:00 | Home Team | score | Away Team |
#
# We extract the two team names around the score.
# ------------------------------------------------------------

def parse_results(results_text):

    results = []

    # Match each dated result row.
    result_pattern = re.compile(
        r"\|\s*[A-Z]\s*\|\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+(\d{1,2}:\d{2})\s*\|"
        r"(.*?)(?=\|\s*[A-Z]\s*\|\s*\d{2}/\d{2}/\d{2,4}\s+\d{1,2}:\d{2}\s*\||\Z)",
        re.DOTALL
    )

    for match in result_pattern.finditer(results_text):

        date_text = match.group(1)
        time_text = match.group(2)
        block = match.group(3)

        # Scores normally appear as:
        #
        # 5 - 1
        #
        score_match = re.search(
            r"(\d+)\s*-\s*(\d+)",
            block
        )

        if not score_match:
            continue

        home_score = int(score_match.group(1))
        away_score = int(score_match.group(2))

        # ----------------------------------------------------
        # First try normal Markdown links.
        #
        # The results page normally contains:
        #
        # [Home Team](...)
        # [5 - 1](...)
        # [Away Team](...)
        # ----------------------------------------------------

        links = re.findall(
            r"\[([^\]]+)\]\(\s*([^)]+)\s*\)",
            block
        )

        team_names = []

        for label, url in links:

            label = clean_name(label)

            if not label:
                continue

            # Ignore score links and obvious navigation.
            if re.fullmatch(r"\d+\s*-\s*\d+(?:\s*\(HT[^)]*\))?", label):
                continue

            if label.upper() in ("VS", "V"):
                continue

            # Ignore fixture links that are not team names.
            if "displayFixture.html" in url:
                team_names.append(label)
            elif "displayCountyFixture.html" in url:
                team_names.append(label)

        # ----------------------------------------------------
        # If normal links did not give us both teams, use
        # image alt text around the score.
        # ----------------------------------------------------

        if len(team_names) < 2:

            alt_names = re.findall(
                r"!\[Image[^:]*:\s*([^\]]+)\]\([^)]+\)",
                block
            )

            alt_names = [
                clean_name(name)
                for name in alt_names
                if clean_name(name)
            ]

            if len(alt_names) >= 2:
                team_names = alt_names[:2]

        # ----------------------------------------------------
        # Last fallback:
        # remove Markdown and use table cells.
        # ----------------------------------------------------

        if len(team_names) < 2:

            plain = block

            plain = re.sub(
                r"!\[[^\]]*\]\([^)]+\)",
                "",
                plain
            )

            plain = re.sub(
                r"\[[^\]]+\]\([^)]+\)",
                lambda m: m.group(0).split("](")[0][1:],
                plain
            )

            cells = [
                clean_name(x)
                for x in plain.split("|")
                if clean_name(x)
            ]

            possible_teams = []

            for cell in cells:

                if re.fullmatch(r"\d+\s*-\s*\d+(?:\s*\(HT[^)]*\))?", cell):
                    continue

                if cell.upper() in ("VS", "V"):
                    continue

                if cell.upper() in ("L", "C", "F", "P"):
                    continue

                if len(cell) > 2:
                    possible_teams.append(cell)

            if len(possible_teams) >= 2:
                team_names = possible_teams[:2]

        if len(team_names) < 2:
            continue

        home = team_names[0]
        away = team_names[1]

        # Only keep Flames results.
        if not is_flames(home) and not is_flames(away):
            continue

        results.append({
            "date": date_text,
            "time": time_text,
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "url": "",
        })

    return results


results = parse_results(results_text)


# Remove duplicate results
result_unique = {}

for result in results:

    key = (
        result["date"],
        result["time"],
        normalise_team_name(result["home"]),
        normalise_team_name(result["away"]),
        result["home_score"],
        result["away_score"],
    )

    result_unique[key] = result

results = list(result_unique.values())


# ------------------------------------------------------------
# Sort future fixtures
# ------------------------------------------------------------

fixtures.sort(
    key=lambda fixture:
        parse_date_time(fixture["date"], fixture["time"])
        or datetime.max
)


# ------------------------------------------------------------
# Sort results
# ------------------------------------------------------------

results.sort(
    key=lambda result:
        parse_date_time(result["date"], result["time"])
        or datetime.max
)


print()
print("=" * 60)
print("FLAMES RESULTS FOUND:", len(results))
print("=" * 60)

for result in results:
    print(
        result["date"],
        result["time"],
        "-",
        result["home"],
        result["home_score"],
        "-",
        result["away_score"],
        result["away"]
    )


print()
print("=" * 60)
print("FLAMES FUTURE FIXTURES FOUND:", len(fixtures))
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
# Remove future fixtures which already have a result
#
# This prevents a completed match appearing twice.
# ------------------------------------------------------------

completed_keys = set()

for result in results:

    completed_keys.add(
        (
            result["date"],
            result["time"],
            normalise_team_name(result["home"]),
            normalise_team_name(result["away"]),
        )
    )


future_fixtures = []

for fixture in fixtures:

    key = (
        fixture["date"],
        fixture["time"],
        normalise_team_name(fixture["home"]),
        normalise_team_name(fixture["away"]),
    )

    if key not in completed_keys:
        future_fixtures.append(fixture)


fixtures = future_fixtures


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
    "X-WR-CALDESC:Pannal Ash U14 Girls Flames fixtures and results",
    "X-WR-TIMEZONE:Europe/London",
]

now = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


# ------------------------------------------------------------
# Add completed results
# ------------------------------------------------------------

for result in results:

    dt = parse_date_time(
        result["date"],
        result["time"]
    )

    if dt is None:
        continue

    end = dt + timedelta(minutes=90)

    # Results have no fixture URL in the results table,
    # so use a stable UID based on date, teams and score.

    uid_base = (
        f"{result['date']}-"
        f"{result['time']}-"
        f"{result['home']}-"
        f"{result['away']}"
    )

    uid = (
        re.sub(r"\W+", "", uid_base)
        + "@pannal-ash-flames-calendar"
    )

    summary = (
        f"{result['home']} "
        f"{result['home_score']} - "
        f"{result['away_score']} "
        f"{result['away']}"
    )

    description = (
        f"Result: {result['home']} "
        f"{result['home_score']} - "
        f"{result['away_score']} "
        f"{result['away']}"
    )

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(description)}",
        "END:VEVENT",
    ])


# ------------------------------------------------------------
# Add future fixtures
# ------------------------------------------------------------

for fixture in fixtures:

    dt = parse_date_time(
        fixture["date"],
        fixture["time"]
    )

    if dt is None:
        continue

    end = dt + timedelta(minutes=90)

    # Use a stable UID based on the FA fixture ID.

    fixture_id_match = re.search(
        r"id=(\d+)",
        fixture["url"]
    )

    if fixture_id_match:
        fixture_id = fixture_id_match.group(1)
    else:
        fixture_id = re.sub(
            r"\W+",
            "",
            fixture["url"]
        )

    uid = (
        f"{fixture_id}"
        "@pannal-ash-flames-calendar"
    )

    summary = (
        f"{fixture['home']} v {fixture['away']}"
    )

    description = (
        f"FA Full-Time fixture: "
        f"{fixture['home']} v {fixture['away']}\\n"
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


# ------------------------------------------------------------
# Finish calendar
# ------------------------------------------------------------

lines.append("END:VCALENDAR")


# ------------------------------------------------------------
# Write calendar
# ------------------------------------------------------------

OUTPUT.parent.mkdir(
    parents=True,
    exist_ok=True
)

OUTPUT.write_text(
    "\r\n".join(lines) + "\r\n",
    encoding="utf-8"
)


print()
print("=" * 60)
print("CALENDAR CREATED")
print("=" * 60)
print("Results written:", len(results))
print("Future fixtures written:", len(fixtures))
print("Total events written:", len(results) + len(fixtures))
print("File:", OUTPUT)
print("File size:", OUTPUT.stat().st_size, "bytes")
