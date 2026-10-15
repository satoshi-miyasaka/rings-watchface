#!/usr/bin/env python3
"""Generates the watch face XML and image resources.

The ring geometry, the slits and the holiday list are computed here so that
they stay consistent, and so that the holiday list can be extended by
changing HOLIDAY_YEARS and re-running:

    python3 tools/generate_watchface.py

Outputs:
    app/src/main/res/raw/watchface.xml
    app/src/main/res/drawable-nodpi/hand_*.png
    app/src/main/res/drawable-nodpi/preview.png
"""

import datetime as dt
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "app" / "src" / "main" / "res"

SIZE = 450
C = SIZE / 2
RING_WIDTH = 13.5
BG = "#FF000000"

# Rings from the outside in: radius, colour, number of slits.
RINGS = {
    "sec": (204.0, "FF6B5B", 12),
    "min": (181.5, "FFD166", 12),
    "hour": (159.0, "5FD4E6", 12),
    "dow": (136.5, "7EE081", 7),
    "week": (114.0, "B28CFF", 7),
}
TRACK_ALPHA = "4D"  # 30 %
SUNDAY_HOLIDAY = "F2FF8FA3"
SATURDAY = "F26FA8FF"

HOLIDAY_YEARS = range(2026, 2031)

# Triangle marker size per ring (seconds is a little smaller).
MARKER = {"sec": 8.4, "min": 10.3, "hour": 10.3, "dow": 10.3}


# ---------------------------------------------------------------- holidays

def _nth_monday(year, month, n):
    d = dt.date(year, month, 1)
    d += dt.timedelta(days=(7 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def japanese_holidays(year):
    """Japanese public holidays for a year (1980-2099 equinox formula)."""
    spring = int(20.8431 + 0.242194 * (year - 1980) - int((year - 1980) / 4))
    autumn = int(23.2488 + 0.242194 * (year - 1980) - int((year - 1980) / 4))
    days = {
        dt.date(year, 1, 1),
        _nth_monday(year, 1, 2),
        dt.date(year, 2, 11),
        dt.date(year, 2, 23),
        dt.date(year, 3, spring),
        dt.date(year, 4, 29),
        dt.date(year, 5, 3),
        dt.date(year, 5, 4),
        dt.date(year, 5, 5),
        _nth_monday(year, 7, 3),
        dt.date(year, 8, 11),
        _nth_monday(year, 9, 3),
        dt.date(year, 9, autumn),
        _nth_monday(year, 10, 2),
        dt.date(year, 11, 3),
        dt.date(year, 11, 23),
    }
    # Citizens' holiday: a weekday sandwiched between two holidays.
    for d in sorted(days):
        mid = d + dt.timedelta(days=1)
        if mid not in days and mid + dt.timedelta(days=1) in days and mid.weekday() != 6:
            days.add(mid)
    # Substitute holiday: a holiday on Sunday moves to the next non-holiday.
    for d in sorted(days):
        if d.weekday() == 6:
            sub = d + dt.timedelta(days=1)
            while sub in days:
                sub += dt.timedelta(days=1)
            days.add(sub)
    return sorted(days)


def ring_index(d):
    """Weekday ring position: Sunday = 0 ... Saturday = 6."""
    return (d.weekday() + 1) % 7


# ---------------------------------------------------------------- XML helpers

def arc(r, start, end, color, width=RING_WIDTH):
    return (
        f'<Arc centerX="{C}" centerY="{C}" width="{2 * r}" height="{2 * r}" '
        f'startAngle="{start:.2f}" endAngle="{end:.2f}">'
        f'<Stroke color="#{color}" thickness="{width}" cap="BUTT"/></Arc>'
    )


def part_draw(name, body):
    return (
        f'<PartDraw name="{name}" x="0" y="0" width="{SIZE}" height="{SIZE}">'
        f"{body}</PartDraw>"
    )


def point(angle, r):
    a = math.radians(angle)
    return C + r * math.sin(a), C - r * math.cos(a)


def slits(r, n):
    out = []
    thick = 1.8 if n > 12 else 3.3
    for i in range(n):
        a = i * 360 / n
        x1, y1 = point(a, r - RING_WIDTH / 2 - 1.5)
        x2, y2 = point(a, r + RING_WIDTH / 2 + 1.5)
        out.append(
            f'<Line startX="{x1:.2f}" startY="{y1:.2f}" endX="{x2:.2f}" endY="{y2:.2f}">'
            f'<Stroke color="{BG}" thickness="{thick}"/></Line>'
        )
    return "".join(out)


def text(name, x, y, w, h, size, color, content, weight="BOLD"):
    return (
        f'<PartText name="{name}" x="{x}" y="{y}" width="{w}" height="{h}">'
        f'<Text align="CENTER" ellipsis="TRUE">'
        f'<Font family="SYNC_TO_DEVICE" size="{size}" weight="{weight}" color="#{color}">'
        f"{content}</Font></Text></PartText>"
    )


def template(fmt, *exprs):
    params = "".join(f'<Parameter expression="{e}"/>' for e in exprs)
    return f"<Template>{fmt}{params}</Template>"


DATE_NUM = "([YEAR] * 10000 + [MONTH] * 100 + [DAY])"


def holiday_conditions():
    """One Condition per weekday segment, lit for the 7 days before a holiday.

    The weekday ring always shows the coming 7 days, so a holiday's segment
    lights up from 6 days before it until the day itself ends.
    """
    by_index = {i: [] for i in range(7)}
    for year in HOLIDAY_YEARS:
        for d in japanese_holidays(year):
            idx = ring_index(d)
            if idx == 0:
                continue  # Sundays are always coloured.
            lo = d - dt.timedelta(days=6)
            by_index[idx].append((int(lo.strftime("%Y%m%d")), int(d.strftime("%Y%m%d"))))

    r = RINGS["dow"][0]
    seg = 360 / 7
    out = []
    for idx, ranges in by_index.items():
        if not ranges:
            continue
        terms = " || ".join(f"({DATE_NUM} &gt;= {lo} &amp;&amp; {hi} &gt;= {DATE_NUM})" for lo, hi in ranges)
        out.append(
            "<Condition><Expressions>"
            f'<Expression name="holiday{idx}"><![CDATA[{terms.replace("&gt;", ">").replace("&amp;", "&")}]]></Expression>'
            "</Expressions>"
            f'<Compare expression="holiday{idx}">'
            + part_draw(f"holiday{idx}", arc(r, idx * seg, (idx + 1) * seg, SUNDAY_HOLIDAY))
            + "</Compare></Condition>"
        )
    return "".join(out)


# ---------------------------------------------------------------- watch face

def watchface_xml():
    seg = 360 / 7
    tracks = "".join(arc(r, 0, 360, TRACK_ALPHA + col) for r, col, _ in RINGS.values())
    weekend = arc(RINGS["dow"][0], 0, seg, SUNDAY_HOLIDAY) + arc(RINGS["dow"][0], 6 * seg, 360, SATURDAY)
    all_slits = "".join(slits(r, n) for r, _, n in RINGS.values())

    weekday_angle = "(([DAY_OF_WEEK] - 1) + [HOUR_0_23_MINUTE] / 24) * 360 / 7"

    date_text = text("date", 135, 160, 180, 30, 17, "FF8B93A1",
                     template("%d月%d日 %s", "[MONTH]", "[DAY]", "[DAY_OF_WEEK_S]"))
    weather = (
        "<Condition><Expressions>"
        '<Expression name="weather"><![CDATA[[WEATHER.IS_AVAILABLE] && !([WEATHER.IS_ERROR])]]></Expression>'
        "</Expressions>"
        '<Compare expression="weather">'
        + text("weatherText", 125, 196, 200, 44, 30, "FFE8EBF0",
               template("%d° %s", "[WEATHER.TEMPERATURE]", "[WEATHER.CONDITION_NAME]"), weight="MEDIUM")
        + "</Compare><Default>"
        + text("weatherNone", 125, 196, 200, 44, 30, "FF8B93A1", "--°", weight="MEDIUM")
        + "</Default></Condition>"
    )

    event_text = template("%s %s", "[COMPLICATION.TITLE]", "[COMPLICATION.TEXT]")
    complication = (
        '<ComplicationSlot slotId="0" name="nextEvent" displayName="@string/next_event" '
        'x="135" y="246" width="180" height="34" supportedTypes="LONG_TEXT SHORT_TEXT" isCustomizable="TRUE">'
        '<DefaultProviderPolicy defaultSystemProvider="NEXT_EVENT" defaultSystemProviderType="LONG_TEXT"/>'
        '<BoundingBox x="0" y="0" width="180" height="34"/>'
        '<Complication type="LONG_TEXT">'
        + text("eventLong", 0, 0, 180, 34, 16, "FF5FD4E6", event_text)
        + "</Complication>"
        '<Complication type="SHORT_TEXT">'
        + text("eventShort", 0, 0, 180, 34, 16, "FF5FD4E6", event_text)
        + "</Complication></ComplicationSlot>"
    )

    full = f'x="0" y="0" width="{SIZE}" height="{SIZE}" pivotX="0.5" pivotY="0.5"'
    hands = (
        f"<AnalogClock {full}>"
        f'<HourHand resource="hand_hour" {full}/>'
        f'<MinuteHand resource="hand_min" {full}/>'
        f'<SecondHand resource="hand_sec" {full}>'
        '<Variant mode="AMBIENT" target="alpha" value="0"/>'
        '<Sweep frequency="5"/></SecondHand>'
        "</AnalogClock>"
        f'<PartImage name="weekdayMarker" {full}>'
        f'<Transform target="angle" value="{weekday_angle}"/>'
        '<Image resource="hand_dow"/></PartImage>'
    )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by tools/generate_watchface.py. Edit the script, not this file. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="ANALOG"/>
  <Metadata key="PREVIEW_TIME" value="10:08:32"/>
  <Scene backgroundColor="{BG}">
    <Group name="rings" {full}>
      <Variant mode="AMBIENT" target="alpha" value="110"/>
      {part_draw("tracks", tracks)}
      {part_draw("weekend", weekend)}
      {holiday_conditions()}
      {part_draw("slits", all_slits)}
    </Group>
    <Group name="center" {full}>
      {date_text}
      {weather}
    </Group>
    {complication}
    {hands}
  </Scene>
</WatchFace>
"""


# ---------------------------------------------------------------- images

SS = 4  # supersampling


def marker_png(ring):
    r = RINGS[ring][0]
    s = MARKER[ring]
    rb = r + s * 0.75
    half = s * 0.95
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pts = [(C, C - (r - s)), (C - half, C - rb), (C + half, C - rb)]
    pts = [(x * SS, y * SS) for x, y in pts]
    d.polygon(pts, fill=(255, 255, 255, 255), outline=(0, 0, 0, 255), width=int(1.5 * SS))
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    img.save(RES / "drawable-nodpi" / f"hand_{ring}.png", optimize=True)


def preview_png():
    """Static preview at 10:08:32 on Thursday 15 October."""
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 255))

    def ring_arc(r, a0, a1, rgba):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        box = [(C - r) * SS, (C - r) * SS, (C + r) * SS, (C + r) * SS]
        ImageDraw.Draw(layer).arc(box, a0 - 90, a1 - 90, fill=rgba, width=int(RING_WIDTH * SS))
        img.alpha_composite(layer)

    def rgba(argb):
        return tuple(int(argb[i:i + 2], 16) for i in (2, 4, 6, 0))

    for r, col, _ in RINGS.values():
        ring_arc(r, 0, 360, rgba(TRACK_ALPHA + col))
    seg = 360 / 7
    ring_arc(RINGS["dow"][0], 0, seg, rgba(SUNDAY_HOLIDAY))
    ring_arc(RINGS["dow"][0], 6 * seg, 360, rgba(SATURDAY))
    d = ImageDraw.Draw(img)
    for r, _, n in RINGS.values():
        thick = 1.8 if n > 12 else 3.3
        for i in range(n):
            a = i * 360 / n
            x1, y1 = point(a, r - RING_WIDTH / 2 - 1.5)
            x2, y2 = point(a, r + RING_WIDTH / 2 + 1.5)
            d.line([(x1 * SS, y1 * SS), (x2 * SS, y2 * SS)], fill=(0, 0, 0, 255), width=int(thick * SS))

    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    angles = {"sec": 32 * 6, "min": (8 + 32 / 60) * 6, "hour": (10 + 8 / 60) * 30, "dow": (4 + 10 / 24) * 360 / 7}
    for ring, ang in angles.items():
        marker = Image.open(RES / "drawable-nodpi" / f"hand_{ring}.png")
        img.alpha_composite(marker.rotate(-ang, resample=Image.BICUBIC, center=(C, C)))

    d = ImageDraw.Draw(img)
    for path in ("/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc", "DejaVuSans-Bold.ttf"):
        try:
            small = ImageFont.truetype(path, 16)
            big = ImageFont.truetype(path, 30)
            break
        except OSError:
            continue
    else:
        small = big = ImageFont.load_default()
    d.text((C, 175), "10月15日 木", font=small, fill=(139, 147, 161, 255), anchor="mm")
    d.text((C, 218), "18° 晴れ", font=big, fill=(232, 235, 240, 255), anchor="mm")
    d.text((C, 263), "14:00 デザインレ…", font=small, fill=(95, 212, 230, 255), anchor="mm")
    img.convert("RGB").save(RES / "drawable-nodpi" / "preview.png", optimize=True)


def main():
    (RES / "raw").mkdir(parents=True, exist_ok=True)
    (RES / "drawable-nodpi").mkdir(parents=True, exist_ok=True)
    (RES / "raw" / "watchface.xml").write_text(watchface_xml(), encoding="utf-8")
    for ring in MARKER:
        marker_png(ring)
    preview_png()


if __name__ == "__main__":
    main()
