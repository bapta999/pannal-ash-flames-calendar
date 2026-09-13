import re
import requests
from pathlib import Path
from datetime import datetime, timedelta

TEAM_URL = "https://fulltime.thefa.com/displayTeam.html?id=101016902"

RESULTS_URL = (
    "https://fulltime.thefa.com/index.html"
    "?league=4051434"
    "&selectedCompetition=0"
    "&selectedDivision=113697267"
    "&selectedFixtureGroupKey=1_925809922"
    "&selectedSeason=41815654"
)

OUTPUT = Path("docs/pannal-ash-flames.ics")

FLAMES = "Pannal Ash JFC U14 Girls Flames"

URL = "https://r.jina.ai/" + TEAM_URL
RESULTS_PAGE_URL = "https://r.jina.ai/" + RESULTS_URL

print("=" * 60)
print("PANNAL ASH FLAMES CALENDAR")
print("=" * 60)

# ------------------------------------------------------------
# Download the FA Full-Time team page
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
# Download the FA Full-Time results page
# ------------------------------------------------------------

results_response = requests.get(
    RESULTS_PAGE_URL,
    timeout=60,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

results_response.raise_for_status()

results_text = results_response.text

print("Results page downloaded successfully")
print("Result page characters downloaded:", len(results_text))


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean_name(value):
    value = re.sub(
        r'!\[Image\s*\d*\s*:\s*([^\]]+)\]\([^)]*\)',
        r'\1',
        value,
        flags=re.IGNORECASE
    )

    value = re.sub(
        r'\[([^\]]+)\]\([^)]*\)',
        r'\1',
        value
    )

    value = re.sub(
        r'https?://\S+',
        '',
        value
    )

    value = re.sub(
        r'\s+',
        ' ',
        value
    )

    return value.strip(" |:-")


def normalise_team_name(name):
    name = clean_name(name)

    # Full-Time can sometimes display the team name differently.
    # We only normalise the Flames name here so that "Flashes"
    # is never accidentally treated as our team.
    if re.search(
        r'Pannal Ash JFC U14 Girls Flames',
        name,
        re.IGNORECASE
    ):
        return FLAMES

    return name


def is_our_team(name):
    return normalise_team_name(name).lower() == FLAMES.lower()


def parse_datetime(date_text, time_text):

    for fmt in ("%d/%m/%y %H:%M", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(
                f"{date_text} {time_text}",
                fmt
            )
        except ValueError:
            pass

    return None


def parse_date_only(line):
    match = re.search(
        r'(\d{2}/\d{2}/\d{2,4})',
        line
    )

    if not match:
        return None

    return match.group(1)


def find_fixture_url(line):
    match = re.search(
        r'https://fulltime\.thefa\.com/'
        r'(?:displayFixture|displayCountyFixture)\.html'
        r'\?id=\d+[^)\s]*',
        line
    )

    return match.group(0) if match else ""


# ------------------------------------------------------------
# Find fixtures from the team page
#
# This deliberately retains the existing working Pannal
# fixture parser.
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

    # Normal Full-Time fixtures use displayFixture.html.
    # Cup fixtures can use displayCountyFixture.html.
    team_links = re.findall(
        r"\[([^\]]+)\]\(\s*"
        r"(https://fulltime\.thefa\.com/"
        r"(?:displayFixture|displayCountyFixture)\.html\?id=\d+[^)]*)"
        r"\s*\)",
        block
    )

    if len(team_links) < 2:
        continue

    home = normalise_team_name(team_links[0][0].strip())
    fixture_url = team_links[0][1].strip()

    away = normalise_team_name(team_links[1][0].strip())

    # We only want fixtures involving the FLAMES.
    #
    # This deliberately excludes:
    # Pannal Ash JFC U14 Girls Flashes v Other Team
    #
    # But includes:
    # Pannal Ash JFC U14 Girls Flashes v Pannal Ash JFC U14 Girls Flames

    if not is_our_team(home) and not is_our_team(away):
        continue

    fixtures.append({
        "date": date_text,
        "time": time_text,
        "home": home,
        "away": away,
        "home_score": None,
        "away_score": None,
        "url": fixture_url,
    })


# ------------------------------------------------------------
# Parse completed results
#
# The results page has lines like:
#
# L 05/09/26[Pannal Ash JFC U14 Girls Flames](...)
# ![Image ...](...)
# [3 - 1](...)
# ![Image ...](...)
# [OPPONENT](...)
#
# We identify the score and use the normal links immediately
# around it to obtain the two team names.
# ------------------------------------------------------------

def parse_results(results_text):

    results = []

    for line in results_text.splitlines():

        date_text = parse_date_only(line)

        if not date_text:
            continue

        # Find a numeric score.
        score_match = re.search(
            r'(\d+)\s*[-–]\s*(\d+)',
            line
        )

        if not score_match:
            continue

        home = ""
        away = ""

        # Get all normal Markdown links.
        links = re.findall(
            r'\[([^\]]+)\]\('
            r'(https://fulltime\.thefa\.com/'
            r'(?:displayFixture|displayCountyFixture)\.html'
            r'\?id=\d+[^)]*)'
            r'\)',
            line
        )

        # The score itself is also a Markdown link, so find the
        # position of the score link and use the normal team
        # links immediately before and after it.
        score_link_match = re.search(
            r'\[\s*\d+\s*[-–]\s*\d+\s*\]\(',
            line
        )

        if score_link_match:

            before = line[:score_link_match.start()]
            after = line[score_link_match.end():]

            before_links = re.findall(
                r'\[([^\]]+)\]\('
                r'https://fulltime\.thefa\.com/'
                r'(?:displayFixture|displayCountyFixture)\.html'
                r'\?id=\d+[^)]*\)',
                before
            )

            after_links = re.findall(
                r'\[([^\]]+)\]\('
                r'https://fulltime\.thefa\.com/'
                r'(?:displayFixture|displayCountyFixture)\.html'
                r'\?id=\d+[^)]*\)',
                after
            )

            if before_links:
                home = before_links[-1]

            if after_links:
                away = after_links[0]

        # Fallback to image alt text if the surrounding links
        # aren't available.
        if not home or not away:

            image_names = re.findall(
                r'!\[Image\s*\d*\s*:\s*([^\]]+)\]',
                line,
                flags=re.IGNORECASE
            )

            image_names = [
                normalise_team_name(x)
                for x in image_names
            ]

            image_names = [
                x for x in image_names
                if x
            ]

            if len(image_names) >= 2:
                home = image_names[0]
                away = image_names[1]

        home = normalise_team_name(home)
        away = normalise_team_name(away)

        if not home or not away:
            continue

        if not is_our_team(home) and not is_our_team(away):
            continue

        home_score = int(score_match.group(1))
        away_score = int(score_match.group(2))

        fixture_url = find_fixture_url(line)

        results.append({
            "date": date_text,
            "time": "10:00",
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "url": fixture_url,
        })

    return results


results = parse_results(results_text)


# ------------------------------------------------------------
# Remove duplicates using fixture URL where available
# ------------------------------------------------------------

unique = {}

for fixture in fixtures:

    key = (
        fixture["date"],
        fixture["time"],
        fixture["home"],
        fixture["away"]
    )

    unique[key] = fixture

fixtures = list(unique.values())


# ------------------------------------------------------------
# Remove duplicate results
# ------------------------------------------------------------

unique_results = {}

for result in results:

    key = (
        result["date"],
        result["home"],
        result["away"],
        result["home_score"],
        result["away_score"]
    )

    unique_results[key] = result

results = list(unique_results.values())


# ------------------------------------------------------------
# Merge results with fixtures
#
# If a fixture now has a result, the result replaces the
# upcoming fixture so that the calendar doesn't contain
# both versions of the same match.
# ------------------------------------------------------------

result_keys = {}

for result in results:

    key = (
        result["date"],
        result["home"],
        result["away"]
    )

    result_keys[key] = result


remaining_fixtures = []

for fixture in fixtures:

    key = (
        fixture["date"],
        fixture["home"],
        fixture["away"]
    )

    if key not in result_keys:
        remaining_fixtures.append(fixture)


fixtures = remaining_fixtures


# ------------------------------------------------------------
# Combine results and future fixtures
# ------------------------------------------------------------

events = results + fixtures


# ------------------------------------------------------------
# Sort fixtures chronologically
# ------------------------------------------------------------

def sort_key(event):

    dt = parse_datetime(
        event["date"],
        event["time"]
    )

    if dt:
        return dt

    return datetime.max


events.sort(key=sort_key)


# ------------------------------------------------------------
# Output diagnostics
# ------------------------------------------------------------

print()
print("=" * 60)
print("FLAMES RESULTS FOUND:", len(results))
print("=" * 60)

for result in results:

    print(
        result["date"],
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


print()
print("=" * 60)
print("TOTAL CALENDAR EVENTS:", len(events))
print("=" * 60)


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


for event in events:

    dt = sort_key(event)

    if not dt or dt == datetime.max:
        continue

    # Assume a 90-minute fixture.
    end = dt + timedelta(minutes=90)

    # Use a stable UID based on the FA fixture ID.
    fixture_id_match = re.search(
        r"id=(\d+)",
        event.get("url", "")
    )

    if fixture_id_match:

        fixture_id = fixture_id_match.group(1)

    else:

        fixture_id = re.sub(
            r"\W+",
            "",
            event.get("url", "")
        )

        if not fixture_id:
            fixture_id = (
                event["date"]
                + event["home"]
                + event["away"]
            )

    uid = f"{fixture_id}@pannal-ash-flames-calendar"


    if event["home_score"] is not None:

        summary = (
            f'{event["home"]} '
            f'{event["home_score"]} - {event["away_score"]} '
            f'{event["away"]}'
        )

        description = "Result"

    else:

        summary = (
            f'{event["home"]} v {event["away"]}'
        )

        description = (
            f"FA Full-Time fixture: "
            f'{event["home"]} v {event["away"]}'
        )


    lines.extend([
        "BEGIN:VEVENT",
        f"UID:{ics_escape(uid)}",
        f"DTSTAMP:{now}",
        f"DTSTART;TZID=Europe/London:{dt.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND;TZID=Europe/London:{end.strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{ics_escape(summary)}",
        f"DESCRIPTION:{ics_escape(description)}",
    ])


    if event.get("url"):

        lines.append(
            f"URL:{event['url']}"
        )


    lines.append(
        "END:VEVENT"
    )


lines.append(
    "END:VCALENDAR"
)


# ------------------------------------------------------------
# Write the calendar
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
print("Events written:", len(events))
print("File:", OUTPUT)
print("File size:", OUTPUT.stat().st_size, "bytes")
