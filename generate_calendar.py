import re
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

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
# Helpers
# ------------------------------------------------------------

def clean_name(name):
    """
    Clean a team name taken from Markdown or image alt text.
    """

    name = re.sub(
        r"!\[[^\]]*\]\([^)]+\)",
        "",
        name
    )

    name = re.sub(
        r"\[[^\]]+\]\([^)]+\)",
        "",
        name
    )

    name = name.replace("&nbsp;", " ")
    name = re.sub(r"\s+", " ", name)

    return name.strip()


def normalise_team_name(name):
    """
    Normalise a team name for comparison.
    """

    name = clean_name(name)

    name = name.replace("’", "'")
    name = name.replace("–", "-")
    name = name.replace("—", "-")

    return re.sub(
        r"\s+",
        " ",
        name
    ).strip().lower()


def is_flames(name):
    return (
        normalise_team_name(name)
        == normalise_team_name(FLAMES)
    )


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


def is_score_text(value):

    return bool(
        re.fullmatch(
            r"\d+\s*-\s*\d+(?:\s*\(HT[^)]*\))?",
            value.strip(),
            re.IGNORECASE
        )
    )


def extract_score_from_result_block(block):

    """
    Extract the score specifically from the result table.

    We deliberately only look for a score which is attached
    to a Markdown link. This prevents numbers elsewhere in
    the fixture block, such as pitch dimensions, from being
    mistaken for a football score.
    """

    score_links = re.findall(
        r"\[([^\]]+)\]\(\s*[^)]+\s*\)",
        block
    )

    for label in score_links:

        label = clean_name(label)

        match = re.fullmatch(
            r"(\d+)\s*-\s*(\d+)"
            r"(?:\s*\(HT\s*\d+\s*-\s*\d+\))?",
            label,
            re.IGNORECASE
        )

        if match:

            return (
                int(match.group(1)),
                int(match.group(2))
            )

    return None


def extract_team_names(block):

    """
    Extract the two teams from a fixture/result block.

    The FA page can represent teams as:
      - normal Markdown links
      - image alt text
      - plain table cells
    """

    team_names = []

    # --------------------------------------------------------
    # Normal Markdown links
    # --------------------------------------------------------

    links = re.findall(
        r"\[([^\]]+)\]\(\s*"
        r"(https://fulltime\.thefa\.com/"
        r"display(?:Fixture|CountyFixture)\.html\?id=\d+[^)]*)"
        r"\s*\)",
        block
    )

    for label, url in links:

        label = clean_name(label)

        if not label:
            continue

        if is_score_text(label):
            continue

        team_names.append(label)

    if len(team_names) >= 2:
        return team_names[:2]


    # --------------------------------------------------------
    # Image alt text
    # --------------------------------------------------------

    alt_names = re.findall(
        r"!\[[^\]]*?:\s*([^\]]+)\]\([^)]+\)",
        block
    )

    alt_names = [
        clean_name(name)
        for name in alt_names
        if clean_name(name)
    ]

    if len(alt_names) >= 2:
        return alt_names[:2]


    # --------------------------------------------------------
    # Plain table cells
    # --------------------------------------------------------

    plain = re.sub(
        r"!\[[^\]]*\]\([^)]+\)",
        "",
        block
    )

    plain = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        plain
    )

    cells = [
        clean_name(cell)
        for cell in plain.split("|")
        if clean_name(cell)
    ]

    possible_teams = []

    for cell in cells:

        if is_score_text(cell):
            continue

        if cell.upper() in (
            "VS",
            "V",
            "L",
            "C",
            "F",
            "P"
        ):
            continue

        if len(cell) > 2:
            possible_teams.append(cell)

    if len(possible_teams) >= 2:
        return possible_teams[:2]

    return []


def find_fixture_url(block):

    match = re.search(
        r"https://fulltime\.thefa\.com/"
        r"display(?:Fixture|CountyFixture)\.html\?id=\d+[^)\s]*",
        block
    )

    if match:
        return match.group(0)

    return ""


# ------------------------------------------------------------
# Find the Results and Upcoming Fixtures sections
# ------------------------------------------------------------

results_heading = re.search(
    r"##\s+Latest Results",
    text,
    re.IGNORECASE
)

fixtures_heading = re.search(
    r"##\s+Upcoming Fixtures",
    text,
    re.IGNORECASE
)


# ------------------------------------------------------------
# Results section
# ------------------------------------------------------------

results = []

if results_heading:

    results_start = results_heading.end()

    if fixtures_heading and fixtures_heading.start() > results_start:
        results_end = fixtures_heading.start()
    else:
        results_end = len(text)

    results_section = text[
        results_start:results_end
    ]

    result_pattern = re.compile(
        r"\|\s*[A-Z]\s*\|\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+"
        r"(\d{1,2}:\d{2})\s*\|"
        r"(.*?)(?=\|\s*[A-Z]\s*\|\s*"
        r"\d{2}/\d{2}/\d{2,4}\s+"
        r"\d{1,2}:\d{2}\s*\||\Z)",
        re.DOTALL
    )

    for match in result_pattern.finditer(
        results_section
    ):

        date_text = match.group(1)
        time_text = match.group(2)
        block = match.group(3)

        team_names = extract_team_names(block)

        if len(team_names) < 2:
            continue

        home = team_names[0]
        away = team_names[1]

        if not is_flames(home) and not is_flames(away):
            continue

        score = extract_score_from_result_block(
            block
        )

        if score is None:
            continue

        results.append({
            "date": date_text,
            "time": time_text,
            "home": home,
            "away": away,
            "home_score": score[0],
            "away_score": score[1],
            "url": find_fixture_url(block),
        })


# ------------------------------------------------------------
# Upcoming fixtures section
# ------------------------------------------------------------

fixtures = []

if fixtures_heading:

    fixtures_start = fixtures_heading.end()

    fixtures_section = text[
        fixtures_start:
    ]

    fixture_pattern = re.compile(
        r"\|\s*[A-Z]\s*\|\s*"
        r"(\d{2}/\d{2}/\d{2,4})\s+"
        r"(\d{1,2}:\d{2})\s*\|"
        r"(.*?)(?=\|\s*[A-Z]\s*\|\s*"
        r"\d{2}/\d{2}/\d{2,4}\s+"
        r"\d{1,2}:\d{2}\s*\||"
        r"##\s+|\Z)",
        re.DOTALL
    )

    for match in fixture_pattern.finditer(
        fixtures_section
    ):

        date_text = match.group(1)
        time_text = match.group(2)
        block = match.group(3)

        team_names = extract_team_names(block)

        if len(team_names) < 2:
            continue

        home = team_names[0]
        away = team_names[1]

        if not is_flames(home) and not is_flames(away):
            continue

        fixtures.append({
            "date": date_text,
            "time": time_text,
            "home": home,
            "away": away,
            "url": find_fixture_url(block),
        })


# ------------------------------------------------------------
# Remove duplicate results
# ------------------------------------------------------------

unique_results = {}

for result in results:

    key = (
        result["date"],
        result["time"],
        normalise_team_name(result["home"]),
        normalise_team_name(result["away"]),
        result["home_score"],
        result["away_score"],
    )

    unique_results[key] = result

results = list(unique_results.values())


# ------------------------------------------------------------
# Remove duplicate fixtures
# ------------------------------------------------------------

unique_fixtures = {}

for fixture in fixtures:

    key = (
        fixture["date"],
        fixture["time"],
        normalise_team_name(fixture["home"]),
        normalise_team_name(fixture["away"]),
    )

    unique_fixtures[key] = fixture

fixtures = list(unique_fixtures.values())


# ------------------------------------------------------------
# Remove any fixture which already has a result
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


fixtures = [
    fixture
    for fixture in fixtures
    if (
        fixture["date"],
        fixture["time"],
        normalise_team_name(fixture["home"]),
        normalise_team_name(fixture["away"]),
    ) not in completed_keys
]


# ------------------------------------------------------------
# Sort chronologically
# ------------------------------------------------------------

results.sort(
    key=lambda result:
        parse_date_time(
            result["date"],
            result["time"]
        ) or datetime.max
)


fixtures.sort(
    key=lambda fixture:
        parse_date_time(
            fixture["date"],
            fixture["time"]
        ) or datetime.max
)


# ------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------

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
# iCalendar helpers
# ------------------------------------------------------------

def ics_escape(value):

    return (
        str(value)
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r", "")
        .replace("\n", "\\n")
    )


def make_uid(value):

    return (
        re.sub(r"\W+", "", value)
        + "@pannal-ash-flames-calendar"
    )


# ------------------------------------------------------------
# Build calendar
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


now = datetime.now(
    timezone.utc
).strftime("%Y%m%dT%H%M%SZ")


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

    end = dt + timedelta(
        minutes=90
    )

    uid_base = (
        f"{result['date']}-"
        f"{result['time']}-"
        f"{result['home']}-"
        f"{result['away']}"
    )

    uid = make_uid(uid_base)

    summary = (
        f"{result['home']} "
        f"{result['home_score']} - "
        f"{result['away_score']} "
        f"{result['away']}"
    )

    description = (
        f"Result: "
        f"{result['home']} "
        f"{result['home_score']} - "
        f"{result['away_score']} "
        f"{result['away']}"
    )

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/London:"
        f"{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:"
        f"{end.strftime('%Y%m%dT%H%M%S')}",
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

    end = dt + timedelta(
        minutes=90
    )

    fixture_id_match = re.search(
        r"id=(\d+)",
        fixture["url"]
    )

    if fixture_id_match:

        fixture_id = (
            fixture_id_match.group(1)
        )

    else:

        fixture_id = (
            f"{fixture['date']}-"
            f"{fixture['time']}-"
            f"{fixture['home']}-"
            f"{fixture['away']}"
        )

    uid = make_uid(fixture_id)

    summary = (
        f"{fixture['home']} v "
        f"{fixture['away']}"
    )

    description = (
        f"FA Full-Time fixture: "
        f"{fixture['home']} v "
        f"{fixture['away']}\\n"
        f"{fixture['url']}"
    )

    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{uid}",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/London:"
        f"{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:"
        f"{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(description)}",
        f"URL:{fixture['url']}",
        "END:VEVENT",
    ])


# ------------------------------------------------------------
# Finish calendar
# ------------------------------------------------------------

lines.append(
    "END:VCALENDAR"
)


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


# ------------------------------------------------------------
# Final output
# ------------------------------------------------------------

print()
print("=" * 60)
print("CALENDAR CREATED")
print("=" * 60)

print(
    "Results written:",
    len(results)
)

print(
    "Future fixtures written:",
    len(fixtures)
)

print(
    "Total events written:",
    len(results) + len(fixtures)
)

print(
    "File:",
    OUTPUT
)

print(
    "File size:",
    OUTPUT.stat().st_size,
    "bytes"
)
