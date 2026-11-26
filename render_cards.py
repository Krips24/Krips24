#!/usr/bin/env python3
"""Render animated SVG profile cards from the public contribution calendar."""

from __future__ import annotations

import argparse
import base64
import datetime as dt
import html
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
DATA_FILE = ROOT / "contributions.json"
OUTPUT_DIR = ROOT / "cards"
LOGIN = "Krips24"
BLUE, BG, PANEL = "#3b82f6", "#0f172a", "#111c31"
TEXT, MUTED, SUBTLE = "#f8fafc", "#94a3b8", "#64748b"
FONT_SOURCES = (
    ("Poppins", "400", "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-Regular.ttf"),
    ("Poppins", "600", "https://raw.githubusercontent.com/google/fonts/main/ofl/poppins/Poppins-SemiBold.ttf"),
    ("Manrope", "100 900", "https://raw.githubusercontent.com/google/fonts/main/ofl/manrope/Manrope%5Bwght%5D.ttf"),
)
WEEKDAYS = ("Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat")
LINKS = (
    ("github", "GitHub", "Code, cloud & experiments", "GH"),
    ("portfolio", "Portfolio", "Selected work & experience", "↗"),
    ("linkedin", "LinkedIn", "Let's connect professionally", "in"),
)
PROJECTS = (
    ("3-tier-aws", "Scalable 3-Tier AWS App", "Cloud architecture",
     "EC2 + ALB + RDS  /  Auto-scaling  /  Production-ready"),
    ("serverless-backend", "Serverless Backend System", "Event-driven services",
     "AWS Lambda + API Gateway  /  Event-driven  /  Cost-optimized"),
    ("cicd-pipeline", "CI/CD Pipeline Setup", "Automated delivery",
     "GitHub Actions  /  Dockerized apps  /  Zero-downtime"),
)


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def font_css(fonts: dict[str, str]) -> str:
    return "".join(
        f"@font-face{{font-family:'{family}';src:url(data:font/woff;base64,{data}) "
        f"format('woff');font-style:normal;font-weight:{weight};}}"
        for key, data in fonts.items()
        for family, weight in (key.rsplit(":", 1),)
    )


def subset_fonts(characters: str) -> dict[str, str]:
    """Download and subset Google Fonts for embedding in standalone SVGs."""
    executable = shutil.which("pyftsubset")
    if not executable:
        raise RuntimeError("pyftsubset is required; install the fonttools package.")
    result: dict[str, str] = {}
    with tempfile.TemporaryDirectory(prefix="profile-fonts-") as directory:
        temporary = Path(directory)
        for family, weight, url in FONT_SOURCES:
            source, output = temporary / f"{family}-{weight.replace(' ', '-')}.ttf", temporary / f"{family}-{weight.replace(' ', '-')}.woff"
            try:
                request = urllib.request.Request(url, headers={"User-Agent": "profile-card-renderer"})
                with urllib.request.urlopen(request, timeout=30) as response:
                    source.write_bytes(response.read())
                subprocess.run(
                    [executable, str(source), f"--output-file={output}", "--flavor=woff",
                     f"--text={characters}", "--layout-features=*"],
                    check=True, capture_output=True, text=True,
                )
                result[f"{family}:{weight}"] = base64.b64encode(output.read_bytes()).decode("ascii")
            except (OSError, subprocess.CalledProcessError) as error:
                raise RuntimeError(f"Unable to download or subset {family}: {error}") from error
    return result


def svg_start(width: int, height: int, delay: float, static: bool, fonts: dict[str, str]) -> str:
    motion = "" if static else (
        f".reveal{{animation:rise .75s cubic-bezier(.2,.8,.2,1) {delay:.2f}s both;}}"
        ".bar{animation:grow .8s cubic-bezier(.2,.8,.2,1) both;}"
    )
    style = f"""
    <style>{font_css(fonts)}
      *{{box-sizing:border-box}}
      text{{font-family:'Manrope',Arial,sans-serif}}
      .display{{font-family:'Poppins','Manrope',Arial,sans-serif}}
      .reveal{{opacity:1;transform:translateY(0)}}
      .bar{{transform-box:fill-box;transform-origin:bottom}}
      {motion}
      @keyframes rise{{from{{opacity:0;transform:translateY(14px)}}to{{opacity:1;transform:translateY(0)}}}}
      @keyframes grow{{from{{transform:scaleY(.08)}}to{{transform:scaleY(1)}}}}
      @media (prefers-reduced-motion:reduce){{
        *,*::before,*::after{{animation:none!important;transition:none!important}}
        animate,animateTransform,animateMotion,animateColor{{display:none!important}}
      }}
    </style>
    """
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">{style}'


def background(width: int, height: int) -> str:
    return f'<rect x="1" y="1" width="{width-2}" height="{height-2}" rx="22" fill="{BG}" stroke="#1e293b" stroke-width="2"/>'


def indicator(width: int, static: bool, delay: float) -> str:
    if static:
        return ""
    return (
        f'<circle cx="{width-25}" cy="26" r="3" fill="{BLUE}"><animate attributeName="opacity" '
        f'values=".55;1;.55" dur="2.4s" begin="{delay+.2:.2f}s" repeatCount="indefinite"/></circle>'
    )


def portrait_data() -> str | None:
    for filename, mime in (("portrait.png", "image/png"), ("portrait.jpg", "image/jpeg"),
                           ("portrait.jpeg", "image/jpeg")):
        path = ROOT / filename
        if path.is_file():
            return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"
    return None


def render_hero(static: bool, delay: float, fonts: dict[str, str], portrait: str | None) -> str:
    width, height = 960, 220
    portrait_markup = (
        f'<image href="{portrait}" x="760" y="28" width="150" height="164" preserveAspectRatio="xMidYMid slice" clip-path="url(#portrait-clip)"/>'
        if portrait else ""
    )
    animated_line = "" if static else (
        f'<animate attributeName="width" values="34;112;34" dur="3.2s" begin="{delay+.6:.2f}s" repeatCount="indefinite"/>'
    )
    return (
        svg_start(width, height, delay, static, fonts)
        + '<defs><linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">'
        f'<stop stop-color="{BLUE}" stop-opacity=".24"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/>'
        '</linearGradient><clipPath id="portrait-clip"><rect x="760" y="28" width="150" height="164" rx="18"/></clipPath></defs>'
        + background(width, height)
        + '<rect x="2" y="2" width="956" height="216" rx="21" fill="url(#glow)"/>'
        + f'<g class="reveal"><text x="54" y="58" fill="{BLUE}" font-size="13" font-weight="800" letter-spacing="3">CLOUD  /  DEVOPS  /  SYSTEMS</text>'
        + f'<text class="display" x="52" y="123" fill="{TEXT}" font-size="48" font-weight="700">Krapansh</text>'
        + f'<text x="55" y="158" fill="{TEXT}" font-size="17" font-weight="700">Cloud &amp; DevOps Engineer | AWS | System Design</text>'
        + f'<text x="55" y="187" fill="{MUTED}" font-size="14">Building reliable cloud systems and automated delivery.</text></g>'
        + portrait_markup
        + f'<rect x="52" y="198" width="34" height="3" rx="2" fill="{BLUE}">{animated_line}</rect>'
        + indicator(width, static, delay) + "</svg>"
    )


def render_link(link: tuple[str, str, str, str], static: bool, delay: float, fonts: dict[str, str]) -> str:
    _slug, title, caption, icon = link
    width, height = 310, 116
    return (
        svg_start(width, height, delay, static, fonts) + background(width, height)
        + f'<g class="reveal"><circle cx="50" cy="57" r="24" fill="{BLUE}" fill-opacity=".16"/>'
        + f'<text class="display" x="50" y="64" text-anchor="middle" fill="{BLUE}" font-size="18" font-weight="800">{esc(icon)}</text>'
        + f'<text x="91" y="51" fill="{TEXT}" font-size="17" font-weight="800">{esc(title)}</text>'
        + f'<text x="91" y="76" fill="{MUTED}" font-size="11.5">{esc(caption)}</text>'
        + f'<path d="M276 53h8m-4-4 4 4-4 4" fill="none" stroke="{BLUE}" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/></g>'
        + indicator(width, static, delay) + "</svg>"
    )


def normalized_days(data: dict[str, Any]) -> list[tuple[dt.date, int]]:
    result = []
    for item in data.get("days", []):
        try:
            result.append((dt.date.fromisoformat(item["date"]), max(0, int(item.get("count", 0)))))
        except (KeyError, TypeError, ValueError):
            continue
    return sorted(result)


def contribution_metrics(days: list[tuple[dt.date, int]]) -> dict[str, Any]:
    if not days:
        return {"available": False, "months": [], "streak": 0, "active_days": 0, "busiest": "—"}
    counts = dict(days)
    today = dt.date.today()
    streak_date = today if counts.get(today, 0) else today - dt.timedelta(days=1)
    streak = 0
    while counts.get(streak_date, 0) > 0:
        streak += 1
        streak_date -= dt.timedelta(days=1)
    weekday_totals, monthly = Counter(), Counter()
    for day, count in days:
        weekday_totals[day.weekday()] += count
        monthly[day.strftime("%Y-%m")] += count
    busiest = (
        WEEKDAYS[(max(weekday_totals, key=weekday_totals.get) + 1) % 7]
        if any(weekday_totals.values()) else "—"
    )
    month_labels = []
    current = today.year * 12 + today.month - 1
    for offset in range(11, -1, -1):
        year, month_zero = divmod(current - offset, 12)
        month_labels.append((f"{year:04d}-{month_zero+1:02d}", dt.date(year, month_zero+1, 1).strftime("%b")))
    return {
        "available": True,
        "months": [(monthly_key, monthly.get(monthly_key, 0), label) for monthly_key, label in month_labels],
        "streak": streak,
        "active_days": sum(count > 0 for _, count in days),
        "busiest": busiest,
    }


def render_contributions(data: dict[str, Any], static: bool, delay: float, fonts: dict[str, str]) -> str:
    width, height = 960, 268
    metrics = contribution_metrics(normalized_days(data))
    result = (
        svg_start(width, height, delay, static, fonts) + background(width, height)
        + f'<g class="reveal"><text class="display" x="38" y="42" fill="{TEXT}" font-size="20" font-weight="700">Contribution rhythm</text>'
        + f'<text x="39" y="63" fill="{MUTED}" font-size="11">Monthly activity · last 12 months</text>'
    )
    stats = (
        ("CURRENT STREAK", f'{metrics["streak"]} days' if metrics["available"] else "—"),
        ("ACTIVE DAYS", str(metrics["active_days"]) if metrics["available"] else "—"),
        ("BUSIEST WEEKDAY", metrics["busiest"]),
    )
    for index, (label, value) in enumerate(stats):
        x = 515 + index * 139
        result += (
            f'<text x="{x}" y="29" fill="{SUBTLE}" font-size="8.5" font-weight="800" letter-spacing=".8">{label}</text>'
            f'<text x="{x}" y="48" fill="{TEXT}" font-size="15" font-weight="800">{esc(value)}</text>'
        )
    months = metrics["months"] or [("", 0, "")] * 12
    maximum = max((value for _, value, _ in months), default=0) or 1
    chart_x, chart_y, chart_h, bar_w, gap = 48, 203, 93, 43, 26
    for index, (_key, value, label) in enumerate(months):
        x = chart_x + index * (bar_w + gap)
        bar_h = max(3, chart_h * value / maximum) if metrics["available"] else 3
        result += (
            f'<rect x="{x}" y="{chart_y}" width="{bar_w}" height="{chart_h}" rx="6" fill="{PANEL}"/>'
            f'<rect class="bar" x="{x}" y="{chart_y+chart_h-bar_h:.1f}" width="{bar_w}" height="{bar_h:.1f}" rx="6" fill="{BLUE}" style="animation-delay:{delay+.14*index:.2f}s"/>'
            f'<text x="{x+bar_w/2}" y="224" text-anchor="middle" fill="{MUTED}" font-size="10">{label}</text>'
        )
    if not metrics["available"]:
        result += f'<text x="480" y="133" text-anchor="middle" fill="{MUTED}" font-size="13">No contribution data yet · first refresh runs daily</text>'
    return result + "</g>" + indicator(width, static, delay) + "</svg>"


def render_project(project: tuple[str, str, str, str], static: bool, delay: float, fonts: dict[str, str]) -> str:
    _slug, title, subtitle, details = project
    width, height = 960, 164
    return (
        svg_start(width, height, delay, static, fonts)
        + '<defs><linearGradient id="glow" x1="0" y1="0" x2="1" y2="1">'
        f'<stop stop-color="{BLUE}" stop-opacity=".18"/><stop offset="1" stop-color="{BG}" stop-opacity="0"/></linearGradient></defs>'
        + background(width, height) + '<rect x="2" y="2" width="956" height="160" rx="20" fill="url(#glow)"/>'
        + f'<g class="reveal"><rect x="38" y="34" width="42" height="42" rx="12" fill="{BLUE}" fill-opacity=".16"/>'
        + f'<path d="M51 46h16v16H51zM55 42h16v16" fill="none" stroke="{BLUE}" stroke-width="2" stroke-linejoin="round"/>'
        + f'<text x="101" y="48" fill="{BLUE}" font-size="11" font-weight="800" letter-spacing="1.4">{esc(subtitle.upper())}</text>'
        + f'<text class="display" x="101" y="79" fill="{TEXT}" font-size="24" font-weight="700">{esc(title)}</text>'
        + f'<text x="101" y="109" fill="{MUTED}" font-size="13">{esc(details)}</text>'
        + f'<text x="793" y="78" fill="{TEXT}" font-size="12" font-weight="700">Explore project</text>'
        + f'<path d="M913 73h12m-5-5 5 5-5 5" fill="none" stroke="{BLUE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></g>'
        + indicator(width, static, delay) + "</svg>"
    )


def render_graph(data: dict[str, Any], static: bool, delay: float, fonts: dict[str, str]) -> str:
    width, height = 960, 190
    days = normalized_days(data)
    counts = dict(days)
    end = days[-1][0] if days else dt.date.today()
    start = end - dt.timedelta(days=370)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    result = (
        svg_start(width, height, delay, static, fonts) + background(width, height)
        + f'<g class="reveal"><text class="display" x="38" y="38" fill="{TEXT}" font-size="18" font-weight="700">Contribution graph</text>'
        + f'<text x="39" y="58" fill="{MUTED}" font-size="10">Your work, one day at a time</text>'
    )
    x0, y0, cell, step = 65, 77, 9, 12
    months_seen = set()
    for column in range(53):
        week_start = start + dt.timedelta(days=column * 7)
        month_key = (week_start.year, week_start.month)
        if month_key not in months_seen:
            result += f'<text x="{x0+column*step}" y="72" fill="{MUTED}" font-size="9">{week_start.strftime("%b")}</text>'
            months_seen.add(month_key)
        for row in range(7):
            day = week_start + dt.timedelta(days=row)
            if day > end:
                continue
            count = counts.get(day, 0)
            opacity = ".12" if count == 0 else ".38" if count < 3 else ".65" if count < 6 else "1"
            result += (
                f'<rect x="{x0+column*step}" y="{y0+row*step}" width="{cell}" height="{cell}" rx="2" fill="{BLUE}" fill-opacity="{opacity}">'
                f'<title>{day.isoformat()}: {count} contributions</title></rect>'
            )
    result += f'<text x="727" y="169" fill="{MUTED}" font-size="9">Less</text>'
    for index, opacity in enumerate((".12", ".38", ".65", "1")):
        result += f'<rect x="{760+index*15}" y="160" width="10" height="10" rx="2" fill="{BLUE}" fill-opacity="{opacity}"/>'
    result += f'<text x="827" y="169" fill="{MUTED}" font-size="9">More</text></g>'
    return result + indicator(width, static, delay) + "</svg>"


def render_cards(
    data: dict[str, Any], output_dir: Path = OUTPUT_DIR, static: bool = False,
    fonts: dict[str, str] | None = None,
) -> list[Path]:
    fonts = fonts or {}
    output_dir.mkdir(parents=True, exist_ok=True)
    rendered = [("hero.svg", render_hero(static, 0, fonts, portrait_data()))]
    for index, link in enumerate(LINKS, 1):
        rendered.append((f"link-{link[0]}.svg", render_link(link, static, index*.42, fonts)))
    index = 4
    rendered.append(("contributions.svg", render_contributions(data, static, index*.42, fonts)))
    index += 1
    for project in PROJECTS:
        rendered.append((f"repo-{project[0]}.svg", render_project(project, static, index*.42, fonts)))
        index += 1
    rendered.append(("contribution-graph.svg", render_graph(data, static, index*.42, fonts)))
    paths = []
    for filename, svg in rendered:
        path = output_dir / filename
        path.write_text(svg, encoding="utf-8")
        paths.append(path)
    return paths


def refresh_data(token: str) -> dict[str, Any]:
    today = dt.datetime.now(dt.timezone.utc).date()
    start = today - dt.timedelta(days=364)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            totalContributions
            weeks { contributionDays { contributionCount date weekday } }
          }
        }
      }
    }
    """
    payload = json.dumps({
        "query": query,
        "variables": {
            "login": LOGIN, "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{today.isoformat()}T23:59:59Z",
        },
    }).encode()
    request = urllib.request.Request(
        "https://api.github.com/graphql", data=payload,
        headers={
            "Authorization": f"bearer {token}", "Content-Type": "application/json",
            "User-Agent": "Krips24-profile-cards",
        }, method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response_data = json.load(response)
    if response_data.get("errors"):
        raise RuntimeError(f"GitHub GraphQL error: {response_data['errors']}")
    try:
        calendar = response_data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    except (KeyError, TypeError) as error:
        raise RuntimeError(f"GitHub returned no contribution calendar for {LOGIN}.") from error
    data = {
        "login": LOGIN,
        "updated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "total_contributions": calendar["totalContributions"],
        "days": [
            {"date": day["date"], "count": day["contributionCount"], "weekday": day["weekday"]}
            for week in calendar["weeks"] for day in week["contributionDays"]
        ],
    }
    DATA_FILE.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return data


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Install fonttools before rendering: python -m pip install fonttools",
    )
    parser.add_argument("--refresh-data", action="store_true", help="fetch the latest contribution calendar")
    args = parser.parse_args()
    if args.refresh_data:
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            parser.error("--refresh-data requires GITHUB_TOKEN")
        data = refresh_data(token)
    else:
        data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    static = os.environ.get("STATIC") == "1"
    characters = " ".join(
        ["Krapansh", "Cloud & DevOps Engineer", "Building reliable cloud systems and automated delivery.",
         "—·", *(text for link in LINKS for text in link[1:]), *(text for project in PROJECTS for text in project[1:])]
    )
    fonts = subset_fonts(characters)
    paths = render_cards(data, static=static, fonts=fonts)
    print(f"Rendered {len(paths)} cards{' in static mode' if static else ''} to {OUTPUT_DIR}.")


if __name__ == "__main__":
    main()
