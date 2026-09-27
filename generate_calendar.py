import re
import requests
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ------------------------------------------------------------
# PANNAL ASH U14 GIRLS FLAMES
# ------------------------------------------------------------

LEAGUE_ID = "1867937"
SEASON_ID = "41815654"
DIVISION_ID = "308032551"
FIXTURE_GROUP_KEY = "1_925809922"

OUTPUT = Path("docs/pannal-ash-flames.ics")

FLAMES = "Pannal Ash JFC U14 Girls Flames"

API_BASE = "https://fulltime.thefa.com/api/sitecore/DivisionDetails"


print("=" * 60)
print("PANNAL ASH FLAMES CALENDAR")
print("=" * 60)


# ------------------------------------------------------------
# API request helper
# ------------------------------------------------------------

def api_request(endpoint, record_per_page):

    url = (
        f"{API_BASE}/{endpoint}"
    )

    data = {
        "divisionid": DIVISION_ID,
        "leagueid": LEAGUE_ID,
        "TeamID": "null",
        "Days": "all",
        "seasonId": SEASON_ID,
        "offSet": "0",
        "recordPerPage": str(record_per_page),
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "Origin": "https://fulltime.thefa.com",
        "Referer": (
            "https://fulltime.thefa.com/"
            "index.html"
        ),
    }

    print()
    print("Requesting:", endpoint)

    response = requests.post(
        url,
        data=data,
        headers=headers,
        timeout=90
    )

    print(
        "HTTP status:",
        response.status_code
    )

    print(
        "Characters returned:",
        len(response.text)
    )

    response.raise_for_status()

    try:
        result = response.json()

    except ValueError:

        print()
        print("API did not return JSON.")
        print(response.text[:2000])

        raise RuntimeError(
            f"{endpoint} returned a non-JSON response."
        )

    return result


# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------

def clean_name(name):

    if name is None:
        return ""

    name = str(name)

    name = re.sub(
        r"!\[[^\]]*\]\([^)]+\)",
        "",
        name
    )

    name = re.sub(
        r"\[([^\]]+)\]\([^)]+\)",
        r"\1",
        name
    )

    name = name.replace(
        "&nbsp;",
        " "
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    )

    return name.strip()


def normalise_team_name(name):

    name = clean_name(name)

    name = name.replace(
        "’",
        "'"
    )

    name = name.replace(
        "–",
        "-"
    )

    name = name.replace(
        "—",
        "-"
    )

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


def parse_date_value(value):

    if value is None:
        return None

    value = str(value).strip()

    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y-%m-%d",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%S.%f",
    ]

    for fmt in formats:

        try:
            return datetime.strptime(
                value,
                fmt
            )

        except ValueError:
            pass

    return None


def parse_time_value(value):

    if value is None:
        return "10:00"

    value = str(value).strip()

    match = re.search(
        r"(\d{1,2}):(\d{2})",
        value
    )

    if match:

        return (
            f"{int(match.group(1)):02d}:"
            f"{match.group(2)}"
        )

    return "10:00"


def parse_datetime(date_value, time_value):

    date_text = str(
        date_value
    ).strip()

    time_text = parse_time_value(
        time_value
    )

    # Handle dates already containing a time.
    date_match = re.search(
        r"(\d{2}/\d{2}/\d{2,4})",
        date_text
    )

    if date_match:

        date_text = date_match.group(1)

        for fmt in (
            "%d/%m/%Y %H:%M",
            "%d/%m/%y %H:%M",
        ):

            try:

                return datetime.strptime(
                    f"{date_text} {time_text}",
                    fmt
                )

            except ValueError:
                pass

    parsed = parse_date_value(
        date_text
    )

    if parsed is not None:

        return parsed.replace(
            hour=int(time_text[:2]),
            minute=int(time_text[3:5])
        )

    return None


def get_value(record, names):

    if not isinstance(record, dict):
        return None

    lowered = {
        str(key).lower(): value
        for key, value in record.items()
    }

    for name in names:

        if name.lower() in lowered:
            return lowered[name.lower()]

    return None


def first_non_empty(record, names):

    for name in names:

        value = get_value(
            record,
            [name]
        )

        if value is not None:

            value = clean_name(
                value
            )

            if value:
                return value

    return ""


def inspect_record(record):

    if not isinstance(record, dict):
        return

    print()
    print(
        "API record fields:"
    )

    for key, value in record.items():

        print(
            f"  {key}: {value}"
        )


# ------------------------------------------------------------
# Extract list from API response
# ------------------------------------------------------------

def get_record_list(data, possible_keys):

    if isinstance(data, list):
        return data

    if not isinstance(data, dict):
        return []

    for key in possible_keys:

        value = data.get(key)

        if isinstance(value, list):
            return value

    # Search one level down.
    for value in data.values():

        if isinstance(value, dict):

            for key in possible_keys:

                nested = value.get(key)

                if isinstance(nested, list):
                    return nested

    return []


# ------------------------------------------------------------
# Download fixtures
# ------------------------------------------------------------

fixtures_api = api_request(
    "DivisionFixturesFacet",
    500
)


fixtures_raw = get_record_list(
    fixtures_api,
    [
        "LeagueFixture",
        "leagueFixture",
        "Fixtures",
        "fixtures",
        "response",
    ]
)


print()
print(
    "RAW FIXTURE RECORDS:",
    len(fixtures_raw)
)


# ------------------------------------------------------------
# Download results
# ------------------------------------------------------------

results_api = api_request(
    "DivisionResultFacet",
    999
)


results_raw = get_record_list(
    results_api,
    [
        "LeagueResults",
        "leagueResults",
        "Results",
        "results",
        "response",
    ]
)


print()
print(
    "RAW RESULT RECORDS:",
    len(results_raw)
)


# ------------------------------------------------------------
# Parse fixtures
# ------------------------------------------------------------

fixtures = []

printed_fixture_structure = False

for record in fixtures_raw:

    if not isinstance(record, dict):
        continue

    home = first_non_empty(
        record,
        [
            "Home",
            "HomeTeam",
            "HomeTeamName",
            "home",
            "homeTeam",
            "homeTeamName",
        ]
    )

    away = first_non_empty(
        record,
        [
            "Away",
            "AwayTeam",
            "AwayTeamName",
            "away",
            "awayTeam",
            "awayTeamName",
        ]
    )

    if not home or not away:

        # Print the first unfamiliar record so that
        # the parser can be adjusted if the FA changes
        # its API structure.
        if not printed_fixture_structure:

            print()
            print(
                "Could not identify teams in fixture record."
            )

            inspect_record(
                record
            )

            printed_fixture_structure = True

        continue

    if not is_flames(home) and not is_flames(away):
        continue

    date_value = first_non_empty(
        record,
        [
            "Date",
            "FixtureDate",
            "fixtureDate",
            "date",
        ]
    )

    time_value = first_non_empty(
        record,
        [
            "Time",
            "FixtureTime",
            "fixtureTime",
            "time",
        ]
    )

    dt = parse_datetime(
        date_value,
        time_value
    )

    if dt is None:
        continue

    fixture_url = first_non_empty(
        record,
        [
            "FixtureURL",
            "fixtureURL",
            "URL",
            "url",
            "FixtureLink",
            "fixtureLink",
        ]
    )

    fixture_id = first_non_empty(
        record,
        [
            "FixtureID",
            "fixtureID",
            "Id",
            "ID",
            "id",
        ]
    )

    if not fixture_url and fixture_id:

        fixture_url = (
            "https://fulltime.thefa.com/"
            f"displayFixture.html?id={fixture_id}"
        )

    fixtures.append({
        "date": dt.strftime("%d/%m/%y"),
        "time": dt.strftime("%H:%M"),
        "home": home,
        "away": away,
        "url": fixture_url,
    })


# ------------------------------------------------------------
# Parse results
# ------------------------------------------------------------

results = []

printed_result_structure = False

for record in results_raw:

    if not isinstance(record, dict):
        continue

    home = first_non_empty(
        record,
        [
            "Home",
            "HomeTeam",
            "HomeTeamName",
            "home",
            "homeTeam",
            "homeTeamName",
        ]
    )

    away = first_non_empty(
        record,
        [
            "Away",
            "AwayTeam",
            "AwayTeamName",
            "away",
            "awayTeam",
            "awayTeamName",
        ]
    )

    if not home or not away:

        if not printed_result_structure:

            print()
            print(
                "Could not identify teams in result record."
            )

            inspect_record(
                record
            )

            printed_result_structure = True

        continue

    if not is_flames(home) and not is_flames(away):
        continue

    date_value = first_non_empty(
        record,
        [
            "Date",
            "ResultDate",
            "resultDate",
            "date",
        ]
    )

    time_value = first_non_empty(
        record,
        [
            "Time",
            "ResultTime",
            "resultTime",
            "time",
        ]
    )

    dt = parse_datetime(
        date_value,
        time_value
    )

    if dt is None:
        continue

    home_score_value = first_non_empty(
        record,
        [
            "HomeScore",
            "homeScore",
            "HomeGoals",
            "homeGoals",
        ]
    )

    away_score_value = first_non_empty(
        record,
        [
            "AwayScore",
            "awayScore",
            "AwayGoals",
            "awayGoals",
        ]
    )

    try:

        home_score = int(
            re.search(
                r"\d+",
                home_score_value
            ).group()
        )

        away_score = int(
            re.search(
                r"\d+",
                away_score_value
            ).group()
        )

    except (
        AttributeError,
        TypeError,
        ValueError
    ):

        # Some versions of the API provide the
        # complete score in a single field.
        full_score = first_non_empty(
            record,
            [
                "FullScore",
                "fullScore",
                "Score",
                "score",
            ]
        )

        score_match = re.search(
            r"(\d+)\s*[-–]\s*(\d+)",
            full_score
        )

        if not score_match:
            continue

        home_score = int(
            score_match.group(1)
        )

        away_score = int(
            score_match.group(2)
        )

    fixture_url = first_non_empty(
        record,
        [
            "FixtureURL",
            "fixtureURL",
            "URL",
            "url",
            "FixtureLink",
            "fixtureLink",
        ]
    )

    fixture_id = first_non_empty(
        record,
        [
            "FixtureID",
            "fixtureID",
            "Id",
            "ID",
            "id",
        ]
    )

    if not fixture_url and fixture_id:

        fixture_url = (
            "https://fulltime.thefa.com/"
            f"displayFixture.html?id={fixture_id}"
        )

    results.append({
        "date": dt.strftime("%d/%m/%y"),
        "time": dt.strftime("%H:%M"),
        "home": home,
        "away": away,
        "home_score": home_score,
        "away_score": away_score,
        "url": fixture_url,
    })


# ------------------------------------------------------------
# Remove duplicates
# ------------------------------------------------------------

unique_results = {}

for result in results:

    key = (
        result["date"],
        result["time"],
        normalise_team_name(
            result["home"]
        ),
        normalise_team_name(
            result["away"]
        ),
        result["home_score"],
        result["away_score"],
    )

    unique_results[key] = result

results = list(
    unique_results.values()
)


unique_fixtures = {}

for fixture in fixtures:

    key = (
        fixture["date"],
        fixture["time"],
        normalise_team_name(
            fixture["home"]
        ),
        normalise_team_name(
            fixture["away"]
        ),
    )

    unique_fixtures[key] = fixture

fixtures = list(
    unique_fixtures.values()
)


# ------------------------------------------------------------
# Remove fixtures already completed
# ------------------------------------------------------------

completed_keys = set()

for result in results:

    completed_keys.add(
        (
            result["date"],
            result["time"],
            normalise_team_name(
                result["home"]
            ),
            normalise_team_name(
                result["away"]
            ),
        )
    )


fixtures = [
    fixture
    for fixture in fixtures
    if (
        fixture["date"],
        fixture["time"],
        normalise_team_name(
            fixture["home"]
        ),
        normalise_team_name(
            fixture["away"]
        ),
    ) not in completed_keys
]


# ------------------------------------------------------------
# Sort
# ------------------------------------------------------------

def sort_key(event):

    dt = parse_datetime(
        event["date"],
        event["time"]
    )

    return dt or datetime.max


results.sort(
    key=sort_key
)

fixtures.sort(
    key=sort_key
)


# ------------------------------------------------------------
# Diagnostics
# ------------------------------------------------------------

print()
print("=" * 60)
print(
    "FLAMES RESULTS FOUND:",
    len(results)
)
print("=" * 60)

for result in results:

    print(
        f'{result["date"]} '
        f'{result["time"]} - '
        f'{result["home"]} '
        f'{result["home_score"]} - '
        f'{result["away_score"]} '
        f'{result["away"]}'
    )


print()
print("=" * 60)
print(
    "FLAMES FUTURE FIXTURES FOUND:",
    len(fixtures)
)
print("=" * 60)

for fixture in fixtures:

    print(
        f'{fixture["date"]} '
        f'{fixture["time"]} - '
        f'{fixture["home"]} v '
        f'{fixture["away"]}'
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
        re.sub(
            r"\W+",
            "",
            str(value)
        )
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
).strftime(
    "%Y%m%dT%H%M%SZ"
)


# ------------------------------------------------------------
# Add results
# ------------------------------------------------------------

for result in results:

    dt = parse_datetime(
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

    uid = make_uid(
        uid_base
    )

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

    dt = parse_datetime(
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

    uid = make_uid(
        fixture_id
    )

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
    ])

    if fixture["url"]:

        lines.append(
            f"URL:{fixture['url']}"
        )

    lines.append(
        "END:VEVENT"
    )


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
