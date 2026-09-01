from full_time_api import Division

SEASON = 41815654
GROUP = "1_925809922"

division = Division()

fixtures = division.get_formatted_fixtures(
    SEASON,
    GROUP,
    include_tbc_fixtures=True,
    include_cup_fixtures=True,
    date_format="%Y-%m-%d",
    time_format="%H:%M"
)

print("Number of fixtures:", len(fixtures))

for fixture in fixtures:
    print(fixture)
