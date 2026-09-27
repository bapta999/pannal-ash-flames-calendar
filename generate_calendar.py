import json
import re
from pathlib import Path
from datetime import datetime, timedelta, timezone
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# ============================================================
# CONFIG
# ============================================================

DIVISION_ID = "308032551"
SEASON_ID = "41815654"

TEAM_NAME = "Pannal Ash JFC U14 Girls Flames"

OUTPUT = Path("docs/pannal-ash-flames.ics")

FIXTURES_URL = (
    f"https://faapi.jwhsolutions.co.uk/api/Fixtures/"
    f"{DIVISION_ID}/season/{SEASON_ID}"
)

RESULTS_URL = (
    f"https://faapi.jwhsolutions.co.uk/api/Results/"
    f"{DIVISION_ID}/season/{SEASON_ID}"
)


# ============================================================
# HTTP
# ============================================================

def download_json(url):
    print(f"Requesting: {url}")

    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/140.0 Safari/537.36"
            ),
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=60) as response:
            status = response.status
            raw = response.read().decode("utf-8", errors="replace")

    except HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        print(f"HTTP status: {e.code}")
        print(raw[:1000])
        raise

    except URLError as e:
        print(f"ERROR downloading data: {e}")
        raise

    print(f"HTTP status: {status}")
    print(f"Characters returned: {len(raw)}")

    if not raw.strip():
        raise RuntimeError("API returned an empty response.")

    try:
        return json.loads(raw)

    except json.JSONDecodeError:
        print("First 2000 characters:")
        print(raw[:2000])
        raise RuntimeError("API did not return valid JSON.")


# ============================================================
# GENERAL JSON HELPERS
# ============================================================

def clean_name(value):
    if value is None:
        return ""

    value = str(value).strip()

    # Remove markdown/image artefacts if they occur
    value = re.sub(r'!\[([^\]]*)\]\([^)]+\)', r'\1', value)
    value = re.sub(r'(?<!!)\[([^\]]+)\]\(([^)]+)\)', r'\1', value)

    value = re.sub(r"^Image\s+\d+\s*:\s*", "", value, flags=re.I)

    return re.sub(r"\s+", " ", value).strip()


def normalise_team_name(value):
    value = clean_name(value).lower()

    value = value.replace("&", "and")

    # Make comparisons tolerant of punctuation
    value = re.sub(r"[^a-z0-9]+", " ", value)

    return re.sub(r"\s+", " ", value).strip()


NORMALISED_TEAM_NAME = normalise_team_name(TEAM_NAME)


def is_flames(name):
    return normalise_team_name(name) == NORMALISED_TEAM_NAME


def first_non_empty(record, keys):
    if not isinstance(record, dict):
        return None

    # Exact keys first
    for key in keys:
        if key in record and record[key] not in (None, ""):
            return record[key]

    # Then case-insensitive matching
    lowered = {
        str(k).lower(): v
        for k, v in record.items()
    }

    for key in keys:
        value = lowered.get(str(key).lower())

        if value not in (None, ""):
            return value

    return None


def get_value(record, *keys):
    return first_non_empty(record, keys)


def inspect_record(record, label):
    print(f"\n--- {label} ---")

    if isinstance(record, dict):
        print("Keys:")
        for key in record.keys():
            print(f"  {key}")

        print("\nSample:")
        print(json.dumps(record, indent=2, ensure_ascii=False)[:5000])

    else:
        print(type(record).__name__)
        print(str(record)[:5000])


def get_record_list(data):
    """
    The external API may return:
      - a plain list
      - { "fixtures": [...] }
      - { "results": [...] }
      - { "data": [...] }
      - another nested object

    Walk the JSON until we find a useful list of dictionaries.
    """

    if isinstance(data, list):
        return data

    if isinstance(data, dict):

        preferred = [
            "fixtures",
            "results",
            "data",
            "items",
            "records",
            "matches",
        ]

        for key in preferred:
            value = first_non_empty(data, [key])

            if isinstance(value, list):
                return value

        # Search one level deeper
        for value in data.values():

            if isinstance(value, list):
                if value and all(isinstance(x, dict) for x in value):
                    return value

            if isinstance(value, dict):
                result = get_record_list(value)

                if result:
                    return result

    return []


# ============================================================
# DATE / TIME
# ============================================================

def parse_date_value(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # ISO date/time
    try:
        dt = datetime.fromisoformat(
            value.replace("Z", "+00:00")
        )
        return dt.date()
    except ValueError:
        pass

    formats = [
        "%d/%m/%Y",
        "%d/%m/%y",
        "%Y-%m-%d",
        "%d-%m-%Y",
        "%d-%m-%y",
        "%m/%d/%Y",
        "%m/%d/%y",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass

    # Extract date from larger strings
    match = re.search(
        r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b",
        value
    )

    if match:
        day, month, year = match.groups()

        if len(year) == 2:
            year = "20" + year

        try:
            return datetime(
                int(year),
                int(month),
                int(day)
            ).date()
        except ValueError:
            pass

    return None


def parse_time_value(value):
    if value is None:
        return None

    value = str(value).strip()

    if not value:
        return None

    # HH:MM / HH:MM:SS
    match = re.search(
        r"\b(\d{1,2}):(\d{2})(?::(\d{2}))?\b",
        value
    )

    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    # e.g. 10.30
    match = re.search(
        r"\b(\d{1,2})\.(\d{2})\b",
        value
    )

    if match:
        hour = int(match.group(1))
        minute = int(match.group(2))

        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return hour, minute

    return None


def parse_datetime(record):
    combined = get_value(
        record,
        "DateTime",
        "FixtureDateTime",
        "StartDateTime",
        "MatchDateTime",
        "KickOff",
        "Kickoff",
        "Date",
        "FixtureDate",
        "MatchDate",
    )

    date_value = get_value(
        record,
        "Date",
        "FixtureDate",
        "MatchDate",
        "GameDate",
        "date",
    )

    time_value = get_value(
        record,
        "Time",
        "FixtureTime",
        "MatchTime",
        "KickOffTime",
        "KickoffTime",
        "time",
    )

    date = parse_date_value(combined)

    if date is None:
        date = parse_date_value(date_value)

    if date is None:
        return None

    parsed_time = parse_time_value(combined)

    if parsed_time is None:
        parsed_time = parse_time_value(time_value)

    if parsed_time is None:
        hour, minute = 10, 0
    else:
        hour, minute = parsed_time

    return datetime(
        date.year,
        date.month,
        date.day,
        hour,
        minute
    )


# ============================================================
# TEAM NAME EXTRACTION
# ============================================================

HOME_KEYS = [
    "Home",
    "HomeTeam",
    "HomeTeamName",
    "HomeTeamDisplayName",
    "HomeName",
    "homeTeam",
    "homeTeamName",
    "home",
]

AWAY_KEYS = [
    "Away",
    "AwayTeam",
    "AwayTeamName",
    "AwayTeamDisplayName",
    "AwayName",
    "awayTeam",
    "awayTeamName",
    "away",
]


def extract_team_name(value):

    if value is None:
        return ""

    if isinstance(value, str):
        return clean_name(value)

    if isinstance(value, dict):
        name = first_non_empty(
            value,
            [
                "Name",
                "name",
                "TeamName",
                "teamName",
                "DisplayName",
                "displayName",
                "ClubName",
                "clubName",
                "Description",
                "description",
            ]
        )

        if name:
            return clean_name(name)

    return clean_name(value)


def get_home_away(record):

    home = extract_team_name(
        get_value(record, *HOME_KEYS)
    )

    away = extract_team_name(
        get_value(record, *AWAY_KEYS)
    )

    return home, away


# ============================================================
# IDS / URLS
# ============================================================

def get_fixture_url(record):

    value = get_value(
        record,
        "Url",
        "URL",
        "url",
        "FixtureUrl",
        "FixtureURL",
        "fixtureUrl",
        "Link",
        "link",
    )

    if isinstance(value, str) and value.startswith("http"):
        return value

    fixture_id = get_value(
        record,
        "FixtureId",
        "FixtureID",
        "fixtureId",
        "Id",
        "ID",
        "id",
    )

    if fixture_id:
        return (
            "https://fulltime.thefa.com/"
            f"displayFixture.html?id={fixture_id}"
        )

    return ""


# ============================================================
# SCORE
# ============================================================

def get_score(record, home, away):

    home_score = get_value(
        record,
        "HomeScore",
        "HomeGoals",
        "homeScore",
        "homeGoals",
        "HomeResult",
    )

    away_score = get_value(
        record,
        "AwayScore",
        "AwayGoals",
        "awayScore",
        "awayGoals",
        "AwayResult",
    )

    if home_score not in (None, "") and away_score not in (None, ""):
        return str(home_score), str(away_score)

    full_score = get_value(
        record,
        "FullScore",
        "Score",
        "score",
        "Result",
        "result",
    )

    if full_score:
        match = re.search(
            r"(\d+)\s*[-–]\s*(\d+)",
            str(full_score)
        )

        if match:
            return match.group(1), match.group(2)

    return "", ""


# ============================================================
# FIXTURES
# ============================================================

def parse_fixtures(data):

    records = get_record_list(data)

    print(f"Raw fixture records found: {len(records)}")

    if records:
        inspect_record(records[0], "FIRST FIXTURE RECORD")

    fixtures = []

    for record in records:

        if not isinstance(record, dict):
            continue

        home, away = get_home_away(record)

        if not home or not away:
            continue

        # Only Flames games.
        # This automatically includes Flames v Flashes.
        if not is_flames(home) and not is_flames(away):
            continue

        dt = parse_datetime(record)

        if not dt:
            continue

        fixtures.append({
            "date": dt,
            "home": home,
            "away": away,
            "url": get_fixture_url(record),
        })

    return fixtures


# ============================================================
# RESULTS
# ============================================================

def parse_results(data):

    records = get_record_list(data)

    print(f"Raw result records found: {len(records)}")

    if records:
        inspect_record(records[0], "FIRST RESULT RECORD")

    results = []

    for record in records:

        if not isinstance(record, dict):
            continue

        home, away = get_home_away(record)

        if not home or not away:
            continue

        if not is_flames(home) and not is_flames(away):
            continue

        dt = parse_datetime(record)

        if not dt:
            continue

        home_score, away_score = get_score(
            record,
            home,
            away
        )

        results.append({
            "date": dt,
            "home": home,
            "away": away,
            "home_score": home_score,
            "away_score": away_score,
            "url": get_fixture_url(record),
        })

    return results


# ============================================================
# DEDUPLICATION
# ============================================================

def fixture_key(item):
    return (
        item["date"].date(),
        normalise_team_name(item["home"]),
        normalise_team_name(item["away"]),
    )


def dedupe(items):

    seen = set()
    output = []

    for item in items:
        key = fixture_key(item)

        if key in seen:
            continue

        seen.add(key)
        output.append(item)

    return output


# ============================================================
# ICS
# ============================================================

def escape_ics(value):

    value = str(value)

    return (
        value
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def utc_timestamp():

    return datetime.now(timezone.utc).strftime(
        "%Y%m%dT%H%M%SZ"
    )


def local_ics_datetime(dt):

    return dt.strftime("%Y%m%dT%H%M%S")


def create_uid(item):

    return (
        f"{item['date'].strftime('%Y%m%d%H%M')}-"
        f"{normalise_team_name(item['home'])}-"
        f"{normalise_team_name(item['away'])}"
        "@pannal-ash-flames"
    )


def build_ics(results, fixtures):

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

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    for item in results:

        start = item["date"]
        end = start + timedelta(minutes=90)

        if item["home_score"] and item["away_score"]:
            summary = (
                f"{item['home']} "
                f"{item['home_score']} - {item['away_score']} "
                f"{item['away']}"
            )

        else:
            summary = (
                f"{item['home']} v {item['away']}"
            )

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{escape_ics(create_uid(item))}",
            f"DTSTAMP:{utc_timestamp()}",
            f"DTSTART;TZID=Europe/London:{local_ics_datetime(start)}",
            f"DTEND;TZID=Europe/London:{local_ics_datetime(end)}",
            f"SUMMARY:{escape_ics(summary)}",
            f"LOCATION:{escape_ics(item['home'] if is_flames(item['away']) else item['away'])}",
            "STATUS:CONFIRMED",
        ])

        if item.get("url"):
            lines.append(
                f"URL:{item['url']}"
            )

        lines.append("END:VEVENT")

    # --------------------------------------------------------
    # FUTURE FIXTURES
    # --------------------------------------------------------

    for item in fixtures:

        start = item["date"]
        end = start + timedelta(minutes=90)

        summary = (
            f"{item['home']} v {item['away']}"
        )

        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{escape_ics(create_uid(item))}",
            f"DTSTAMP:{utc_timestamp()}",
            f"DTSTART;TZID=Europe/London:{local_ics_datetime(start)}",
            f"DTEND;TZID=Europe/London:{local_ics_datetime(end)}",
            f"SUMMARY:{escape_ics(summary)}",
            "STATUS:CONFIRMED",
        ])

        if item.get("url"):
            lines.append(
                f"URL:{item['url']}"
            )

        lines.append("END:VEVENT")

    lines.append("END:VCALENDAR")

    return "\n".join(lines) + "\n"


# ============================================================
# MAIN
# ============================================================

def main():

    print("==============================================")
    print("PANNAL ASH U14 GIRLS FLAMES CALENDAR")
    print("==============================================")

    print()
    print("Downloading fixtures...")
    fixture_data = download_json(FIXTURES_URL)

    print()
    print("Downloading results...")
    result_data = download_json(RESULTS_URL)

    print()
    print("Parsing fixtures...")
    fixtures = parse_fixtures(fixture_data)

    print()
    print("Parsing results...")
    results = parse_results(result_data)

    # Remove future fixture entries which are already represented
    # by completed results.
    result_keys = {
        fixture_key(result)
        for result in results
    }

    fixtures = [
        fixture
        for fixture in fixtures
        if fixture_key(fixture) not in result_keys
    ]

    fixtures = dedupe(fixtures)
    results = dedupe(results)

    fixtures.sort(key=lambda x: x["date"])
    results.sort(key=lambda x: x["date"])

    print()
    print(f"FLAMES RESULTS FOUND: {len(results)}")
    print(f"FLAMES FUTURE FIXTURES FOUND: {len(fixtures)}")

    print()

    for result in results:
        print(
            f"RESULT: "
            f"{result['date'].strftime('%d/%m/%y %H:%M')} - "
            f"{result['home']} "
            f"{result['home_score']} - {result['away_score']} "
            f"{result['away']}"
        )

    print()

    for fixture in fixtures:
        print(
            f"FIXTURE: "
            f"{fixture['date'].strftime('%d/%m/%y %H:%M')} - "
            f"{fixture['home']} v {fixture['away']}"
        )

    print()
    print("Building calendar...")

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    ics = build_ics(
        results,
        fixtures
    )

    OUTPUT.write_text(
        ics,
        encoding="utf-8"
    )

    print()
    print(f"Calendar written to: {OUTPUT}")
    print(f"Calendar events: {len(results) + len(fixtures)}")
    print()
    print("DONE")


if __name__ == "__main__":
    main()
