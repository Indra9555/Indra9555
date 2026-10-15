
import json
import os
import urllib.request
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

USERNAME = "Indra9555"
OUTPUT = Path("assets/contribution-graph.svg")

BG = "#080B16"
TEXT = "#E6F7FF"
MUTED = "#94A3B8"
EMPTY = "#151D2E"
COLORS = ["#164E63", "#0E7490", "#22D3EE", "#A78BFA"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_calendar():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GITHUB_TOKEN environment variable is missing.")

    payload = json.dumps({
        "query": QUERY,
        "variables": {"login": USERNAME},
    }).encode("utf-8")

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "Indrajeet-Contribution-Graph",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        result = json.loads(response.read().decode("utf-8"))

    if result.get("errors"):
        raise RuntimeError(
            "GitHub GraphQL error: " + json.dumps(result["errors"])
        )

    user = result.get("data", {}).get("user")
    if not user:
        raise RuntimeError(f"GitHub user {USERNAME} was not found.")

    return user["contributionsCollection"]["contributionCalendar"]


def generate_svg(calendar):
    weeks = calendar["weeks"]
    total = calendar["totalContributions"]

    cell = 12
    gap = 4
    step = cell + gap
    left = 42
    top = 47
    width = 1100
    height = 188

    days = [
        day
        for week in weeks
        for day in week["contributionDays"]
    ]
    maximum = max(
        (day["contributionCount"] for day in days),
        default=0,
    )

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {width} {height}" '
        f'width="{width}" height="{height}" role="img">',
        f'<title>GitHub contributions for {USERNAME}</title>',
        f'<rect width="100%" height="100%" rx="14" fill="{BG}"/>',
        f'<text x="24" y="27" fill="{TEXT}" '
        f'font-family="monospace" font-size="16" '
        f'font-weight="bold">CONTRIBUTION ACTIVITY</text>',
        f'<text x="{width - 24}" y="27" text-anchor="end" '
        f'fill="#22D3EE" font-family="monospace" '
        f'font-size="12">{total:,} contributions in the last year</text>',
    ]

    # Weekday labels: Monday, Wednesday and Friday.
    for row, label in [(0, "Mon"), (2, "Wed"), (4, "Fri")]:
        y = top + row * step + cell - 1
        parts.append(
            f'<text x="8" y="{y}" fill="{MUTED}" '
            f'font-family="monospace" font-size="10">{label}</text>'
        )

    previous_month = None

    for col, week in enumerate(weeks):
        x = left + col * step
        first_day = date.fromisoformat(week["contributionDays"][0]["date"])
        month_key = (first_day.year, first_day.month)

        if month_key != previous_month:
            parts.append(
                f'<text x="{x}" y="{top - 10}" fill="{MUTED}" '
                f'font-family="monospace" font-size="10">'
                f'{escape(first_day.strftime("%b"))}</text>'
            )
            previous_month = month_key

        for day in week["contributionDays"]:
            current_date = date.fromisoformat(day["date"])
            count = day["contributionCount"]

            if count == 0 or maximum == 0:
                color = EMPTY
            else:
                ratio = count / maximum
                if ratio <= 0.25:
                    color = COLORS[0]
                elif ratio <= 0.50:
                    color = COLORS[1]
                elif ratio <= 0.75:
                    color = COLORS[2]
                else:
                    color = COLORS[3]

            # Python weekday(): Monday=0, Sunday=6.
            row = current_date.weekday()
            y = top + row * step
            tooltip = escape(f"{current_date.isoformat()}: {count} contributions")

            parts.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'rx="3" fill="{color}">'
                f'<title>{tooltip}</title></rect>'
            )

    # Legend.
    legend_y = 174
    legend_x = width - 190
    parts.append(
        f'<text x="{legend_x - 48}" y="{legend_y + 10}" '
        f'fill="{MUTED}" font-family="monospace" '
        f'font-size="10">Less</text>'
    )

    legend_colors = [EMPTY, *COLORS]
    for index, color in enumerate(legend_colors):
        x = legend_x + index * 17
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="12" height="12" '
            f'rx="3" fill="{color}"/>'
        )

    parts.append(
        f'<text x="{legend_x + 102}" y="{legend_y + 10}" '
        f'fill="{MUTED}" font-family="monospace" '
        f'font-size="10">More</text>'
    )
    parts.append("</svg>")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT} with {total} contributions.")


if __name__ == "__main__":
    generate_svg(fetch_calendar())
