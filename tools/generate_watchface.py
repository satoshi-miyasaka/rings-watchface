#!/usr/bin/env python3
"""Generates the watch face XML and image resources.

The ring geometry, the slits and the holiday list are computed here so that
they stay consistent, and so that the holiday list can be extended by
changing HOLIDAY_YEARS and re-running:

    python3 tools/generate_watchface.py

Outputs:
    app/src/main/res/raw/watchface.xml
    app/src/main/res/drawable-nodpi/hand_*.png (one per ring and marker shape)
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
    "week": (136.5, "B28CFF", 7),
    "dow": (114.0, "7EE081", 7),
}
TRACK_ALPHA = "4D"  # 30 %
SUNDAY_HOLIDAY = "F2FF8FA3"
SATURDAY = "F26FA8FF"

HOLIDAY_YEARS = range(2026, 2031)

# Marker shapes the editor offers for the second, minute and hour hands, and
# each hand's default. Distinct shapes keep the hands apart in ambient mode,
# when the ring colours dim. Sizes are per ring so the shapes stay in proportion.
# "triangle" points at the centre (shown as 内向き), "triangleUp" away from it (外向き).
HAND_SHAPES = {ring: ("triangle", "triangleUp", "dot", "line") for ring in ("sec", "min", "hour")}
HAND_DEFAULT = {"sec": "triangle", "min": "triangle", "hour": "dot"}
TRIANGLE = {"sec": 8.4, "min": 10.3, "hour": 10.3}
DOT = {"sec": 6.0, "min": 6.5, "hour": 7.0}
LINE = 3.9
# The weekday marker is a bar across the week and weekday rings.
DOW_BAR = 3.9

# Bright slits drawn over the black ones of the chosen rings. They stay at
# full brightness in ambient mode, so the time can be read when the rings
# dim. The editor offers these sets of rings and colours.
TICK_SETS = (
    ("secDow", ("sec", "dow")),
    ("all", ("sec", "min", "hour", "week", "dow")),
    ("none", ()),
)
TICK_COLORS = (
    ("white", "FFFFFFFF"),
    ("red", "FFFF5A5A"),
    ("blue", "FF5A9BFF"),
    ("yellow", "FFFFE14D"),
    ("green", "FF5FE07A"),
    ("gray", "FF9AA0A6"),
)
TICK_THICK = {True: 3.6, False: 2.4}  # quarter hours, others

# What the seconds ring can show besides the seconds, as a lit arc from 12
# o'clock: (option id, percentage expression). The phone's battery comes from
# the companion app, so it is drawn inside the minute slot instead.
SEC_VALUES = (
    ("none", None),
    ("steps", "clamp([STEP_PERCENT], 0, 100)"),
    ("watchBattery", "[BATTERY_PERCENT]"),
    ("phoneBattery", None),
)


# The companion app (wear module) packs ring segments into GOAL_PROGRESS
# values; see wear/.../Rings.kt for the layout. Component names of its sources:
COMPANION = "io.github.satoshimiyasaka.rings/io.github.satoshimiyasaka.rings."
LIT_ALPHA = "F2"


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


def tick_lines(rings):
    """(x1, y1, x2, y2, thickness) of each bright slit on the given rings."""
    for ring in rings:
        r, _, n = RINGS[ring]
        for i in range(n):
            a = i * 360 / n
            yield (*point(a, r - RING_WIDTH / 2), *point(a, r + RING_WIDTH / 2),
                   TICK_THICK[n == 12 and i % 3 == 0])


def ticks(rings):
    return "".join(
        f'<Line startX="{x1:.2f}" startY="{y1:.2f}" endX="{x2:.2f}" endY="{y2:.2f}">'
        f'<Stroke color="[CONFIGURATION.tickColor.0]" thickness="{t}"/></Line>'
        for x1, y1, x2, y2, t in tick_lines(rings)
    )


def value_arc(r, color, percent):
    """An arc from 12 o'clock that grows with a 0-100 expression."""
    return (
        f'<Arc centerX="{C}" centerY="{C}" width="{2 * r}" height="{2 * r}" startAngle="0" endAngle="0">'
        f'<Stroke color="#{color}" thickness="{RING_WIDTH}" cap="BUTT"/>'
        f'<Transform target="endAngle" value="({percent}) * 3.6"/></Arc>'
    )


def empty():
    """Nothing; for list options that draw nothing here."""
    return f'<Group name="empty" x="0" y="0" width="{SIZE}" height="{SIZE}"/>'


def sec_value_options(draw):
    """The secValue configuration with draw(option id, expression) per option."""
    return (
        '<ListConfiguration id="secValue">'
        + "".join(f'<ListOption id="{opt}">{draw(opt, expr) or empty()}</ListOption>'
                  for opt, expr in SEC_VALUES)
        + "</ListConfiguration>"
    )


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

V = "[COMPLICATION.GOAL_PROGRESS_VALUE]"
T = "[COMPLICATION.GOAL_PROGRESS_TARGET_VALUE]"


def lit_if(name, expr, body):
    return (
        "<Condition><Expressions>"
        f'<Expression name="{name}"><![CDATA[{expr}]]></Expression>'
        "</Expressions>"
        f'<Compare expression="{name}">{body}</Compare></Condition>'
    )


def bit(field, i):
    """Expression that is true when bit i of a packed complication field is set."""
    return f"floor({field} / {2 ** i}) % 2 == 1"


def data_slot(slot_id, name, source, body):
    """A full-screen slot that only draws, fixed to one of the companion's sources.

    The bounding box has to cover the whole face: the runtime clips what a
    complication draws to its bounding box, and the lit segments sit on the rings.
    The slots are not customizable, so they stay out of the watch face editor.

    Do not add, remove or reorder slots once the closed test has started. The
    watch saves each slot's data source by its position when the face is
    added: reordering hands every slot another slot's data, and a slot added
    later stays empty on watches that update until the face is added again.
    """
    return (
        f'<ComplicationSlot slotId="{slot_id}" name="{name}" displayName="@string/{name}" '
        f'x="0" y="0" width="{SIZE}" height="{SIZE}" supportedTypes="GOAL_PROGRESS" isCustomizable="FALSE">'
        f'<DefaultProviderPolicy defaultSystemProvider="EMPTY" defaultSystemProviderType="GOAL_PROGRESS" '
        f'primaryProvider="{COMPANION}{source}" primaryProviderType="GOAL_PROGRESS"/>'
        f'<BoundingBox x="0" y="0" width="{SIZE}" height="{SIZE}"/>'
        '<Variant mode="AMBIENT" target="alpha" value="110"/>'
        f'<Complication type="GOAL_PROGRESS">{body}</Complication>'
        "</ComplicationSlot>"
    )


def companion_slots():
    hour_r, hour_col, _ = RINGS["hour"]
    min_r, min_col, _ = RINGS["min"]
    week_r, week_col, _ = RINGS["week"]

    # Hour ring: 24 half-hour segments in the value.
    hour = "".join(
        lit_if(f"hourBit{i}", bit(V, i),
               part_draw(f"hourSeg{i}", arc(hour_r, i * 15, (i + 1) * 15, LIT_ALPHA + hour_col)))
        for i in range(24)
    )
    # Minute ring: 60 one-minute segments. Bits 0-23 ride on this slot's
    # target (plus one), bits 24-59 on the minute slot.
    def minute(k, field, shift):
        return lit_if(f"min{k}", bit(field, k - shift),
                      part_draw(f"minSeg{k}", arc(min_r, k * 6, (k + 1) * 6, LIT_ALPHA + min_col)))

    minutes_low = "".join(minute(k, f"({T} - 1)", 0) for k in range(24))
    minutes_high = "".join(minute(k, V, 24) for k in range(24, 48)) + "".join(
        minute(k, f"({T} - 1)", 48) for k in range(48, 60))

    # Week ring: 7 weekdays x 12 two-hour blocks, 24 bits per field.
    seg = 360 / 7
    block = seg / 12

    def week_day(day, field, shift, offset=""):
        expr_field = f"({field}{offset})"
        return "".join(
            lit_if(f"week{day}b{b}", bit(expr_field, shift + b),
                   part_draw(f"week{day}s{b}",
                             arc(week_r, day * seg + b * block, day * seg + (b + 1) * block,
                                 LIT_ALPHA + week_col)))
            for b in range(12)
        )

    week_a = week_day(0, V, 0) + week_day(1, V, 12) + week_day(2, T, 0, " - 1") + week_day(3, T, 12, " - 1")
    week_b = week_day(4, V, 0) + week_day(5, V, 12) + week_day(6, T, 0, " - 1")

    # Days off found in the phone's calendar ("有給" and so on), bit 12 + weekday
    # of week B's target, coloured like holidays on the weekday ring.
    dow_r = RINGS["dow"][0]
    days_off = "".join(
        lit_if(f"dayOff{d}", bit(f"({T} - 1)", 12 + d),
               part_draw(f"dayOff{d}", arc(dow_r, d * seg, (d + 1) * seg, SUNDAY_HOLIDAY)))
        for d in range(7)
    )

    # The phone's battery, bits 12-18 of the minute slot's target, valid when
    # bit 19 is set; shown on the seconds ring when chosen in the editor.
    sec_r, sec_col, _ = RINGS["sec"]
    battery = f"(floor(({T} - 1) / 4096) % 128)"
    phone_battery = (
        f'<Group name="phoneBattery" x="0" y="0" width="{SIZE}" height="{SIZE}">'
        + sec_value_options(lambda opt, _: opt == "phoneBattery" and lit_if(
            "phoneBatteryValid", bit(f"({T} - 1)", 19),
            part_draw("phoneBatteryArc", value_arc(sec_r, LIT_ALPHA + sec_col, battery))))
        + "</Group>"
    )

    return (
        data_slot(1, "ring_hour", "HourRingDataSource", hour + minutes_low)
        + data_slot(2, "ring_week_a", "WeekADataSource", week_a)
        + data_slot(3, "ring_week_b", "WeekBDataSource", week_b + days_off)
    ), data_slot(4, "ring_minute", "MinuteRingDataSource", minutes_high + phone_battery)


def watchface_xml():
    ring_slots, minute_slot = companion_slots()
    seg = 360 / 7
    tracks = "".join(arc(r, 0, 360, TRACK_ALPHA + col) for r, col, _ in RINGS.values())
    weekend = arc(RINGS["dow"][0], 0, seg, SUNDAY_HOLIDAY) + arc(RINGS["dow"][0], 6 * seg, 360, SATURDAY)
    all_slits = "".join(slits(r, n) for r, _, n in RINGS.values())
    sec_r, sec_col, _ = RINGS["sec"]
    sec_value = sec_value_options(
        lambda opt, expr: expr and part_draw(f"{opt}Arc", value_arc(sec_r, LIT_ALPHA + sec_col, expr)))
    tick_marks = (
        '<ListConfiguration id="tickRings">'
        + "".join(f'<ListOption id="{opt}">{part_draw("ticks", ticks(rings)) if rings else empty()}</ListOption>'
                  for opt, rings in TICK_SETS)
        + "</ListConfiguration>"
    )

    def options(ids, prefix, icon):
        return "".join(
            f'<ListOption id="{i}" displayName="@string/{prefix}_{i}" icon="{icon}_{i.lower()}"/>' for i in ids)

    configurations = (
        "<UserConfigurations>"
        f'<ListConfiguration id="tickRings" displayName="@string/cfg_tick_rings" defaultValue="{TICK_SETS[0][0]}">'
        + options([opt for opt, _ in TICK_SETS], "tick_rings", "icon_ticks")
        + "</ListConfiguration>"
        '<ColorConfiguration id="tickColor" displayName="@string/cfg_tick_color" defaultValue="white">'
        + "".join(f'<ColorOption id="{i}" displayName="@string/color_{i}" colors="#{c}"/>' for i, c in TICK_COLORS)
        + "</ColorConfiguration>"
        + "".join(
            f'<ListConfiguration id="hand_{ring}" displayName="@string/cfg_hand_{ring}" '
            f'defaultValue="{HAND_DEFAULT[ring]}">{options(HAND_SHAPES[ring], "shape", "icon_shape")}'
            "</ListConfiguration>"
            for ring in ("sec", "min", "hour")
        )
        + '<ListConfiguration id="secValue" displayName="@string/cfg_sec_value" defaultValue="none">'
        + options([opt for opt, _ in SEC_VALUES], "sec_value", "icon_sec")
        + "</ListConfiguration></UserConfigurations>"
    )

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
    hand_tags = {"hour": "HourHand", "min": "MinuteHand", "sec": "SecondHand"}

    def hand(ring, shape):
        tag = hand_tags[ring]
        inner = ('<Variant mode="AMBIENT" target="alpha" value="0"/><Sweep frequency="5"/>'
                 if ring == "sec" else "")
        return (f"<AnalogClock {full}>"
                f'<{tag} resource="hand_{ring}_{shape.lower()}" {full}>{inner}</{tag}>'
                "</AnalogClock>")

    hands = "".join(
        f'<ListConfiguration id="hand_{ring}">'
        + "".join(f'<ListOption id="{shape}">{hand(ring, shape)}</ListOption>' for shape in HAND_SHAPES[ring])
        + "</ListConfiguration>"
        for ring in ("hour", "min", "sec")
    ) + (
        f'<PartImage name="weekdayMarker" {full}>'
        f'<Transform target="angle" value="{weekday_angle}"/>'
        '<Image resource="hand_dow"/></PartImage>'
    )

    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by tools/generate_watchface.py. Edit the script, not this file. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="ANALOG"/>
  <Metadata key="PREVIEW_TIME" value="10:08:32"/>
  {configurations}
  <Scene backgroundColor="{BG}">
    <Group name="rings" {full}>
      <Variant mode="AMBIENT" target="alpha" value="110"/>
      {part_draw("tracks", tracks)}
      {part_draw("weekend", weekend)}
      {holiday_conditions()}
      {sec_value}
    </Group>
    {ring_slots}
    <Group name="center" {full}>
      {date_text}
      {weather}
    </Group>
    {complication}
    {minute_slot}
    {part_draw("slits", all_slits)}
    {tick_marks}
    {hands}
  </Scene>
</WatchFace>
"""


# ---------------------------------------------------------------- images

SS = 4  # supersampling


def marker_png(ring, shape):
    r = RINGS[ring][0]
    img = Image.new("RGBA", (SIZE * SS, SIZE * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    white, black = (255, 255, 255, 255), (0, 0, 0, 255)
    if shape in ("triangle", "triangleUp"):
        s = TRIANGLE[ring]
        half = s * 0.95
        if shape == "triangle":  # tip towards the centre
            pts = [(C, C - (r - s)), (C - half, C - (r + s * 0.75)), (C + half, C - (r + s * 0.75))]
        else:
            pts = [(C, C - (r + s)), (C - half, C - (r - s * 0.75)), (C + half, C - (r - s * 0.75))]
        pts = [(x * SS, y * SS) for x, y in pts]
        d.polygon(pts, fill=white, outline=black, width=int(1.5 * SS))
    elif shape == "dot":
        s = DOT[ring]
        box = [(C - s) * SS, (C - r - s) * SS, (C + s) * SS, (C - r + s) * SS]
        d.ellipse(box, fill=white, outline=black, width=int(1.5 * SS))
    else:
        if shape == "line":  # across this ring
            s = LINE
            y_out = C - (r + RING_WIDTH / 2 + 1.5)
            y_in = C - (r - RING_WIDTH / 2 - 1.5)
        else:  # bar from the outer edge of the week ring to the inner edge of the weekday ring
            s = DOW_BAR
            y_out = C - (RINGS["week"][0] + RING_WIDTH / 2)
            y_in = C - (r - RING_WIDTH / 2)
        for width, col in ((s + 3.6, black), (s, white)):
            w = width * SS
            d.rounded_rectangle([(C * SS - w / 2, y_out * SS - (w - s * SS) / 2),
                                 (C * SS + w / 2, y_in * SS + (w - s * SS) / 2)], radius=w / 2, fill=col)
    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    name = "hand_dow" if ring == "dow" else f"hand_{ring}_{shape.lower()}"
    img.save(RES / "drawable-nodpi" / f"{name}.png", optimize=True)


ICON = 96  # editor option icons


def option_icons():
    """Images for the editor's option buttons: the shape, the rings or the value."""
    out = RES / "drawable-nodpi"
    k = ICON * SS
    font_path = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"

    def canvas():
        img = Image.new("RGBA", (k, k), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        d.ellipse([0, 0, k - 1, k - 1], fill=(32, 33, 36, 255))
        return img, d

    def save(img, name):  # Android resource names are lower case
        name = name.lower()
        img.resize((ICON, ICON), Image.LANCZOS).save(out / f"{name}.png", optimize=True)

    white, black = (255, 255, 255, 255), (0, 0, 0, 255)
    c, u = k / 2, k / 96  # centre, one icon pixel
    shapes = {s for ring in HAND_SHAPES.values() for s in ring}
    for shape in shapes:
        img, d = canvas()
        if shape == "triangle":
            d.polygon([(c, c + 22 * u), (c - 24 * u, c - 18 * u), (c + 24 * u, c - 18 * u)], fill=white)
        elif shape == "triangleUp":
            d.polygon([(c, c - 22 * u), (c - 24 * u, c + 18 * u), (c + 24 * u, c + 18 * u)], fill=white)
        elif shape == "dot":
            d.ellipse([c - 18 * u, c - 18 * u, c + 18 * u, c + 18 * u], fill=white)
        else:
            d.rounded_rectangle([c - 6 * u, c - 28 * u, c + 6 * u, c + 28 * u], radius=6 * u, fill=white)
        save(img, f"icon_shape_{shape}")

    # Rings in miniature, with the chosen rings' slits.
    scale = (k / 2 - 6 * u) / (RINGS["sec"][0] + RING_WIDTH / 2)
    for opt, rings in TICK_SETS:
        img, d = canvas()
        for ring, (r, col, n) in RINGS.items():
            rr = r * scale
            width = int(RING_WIDTH * scale * 1.4)  # thicker than to scale, to read at icon size
            d.ellipse([c - rr, c - rr, c + rr, c + rr], outline=tuple(int(col[i:i + 2], 16) for i in (0, 2, 4)) + (140,),
                      width=width)
            if ring in rings:
                for i in range(n):
                    a = math.radians(i * 360 / n)
                    p1 = (c + (rr - width / 2) * math.sin(a), c - (rr - width / 2) * math.cos(a))
                    p2 = (c + (rr + width / 2) * math.sin(a), c - (rr + width / 2) * math.cos(a))
                    d.line([p1, p2], fill=white, width=int(4 * u))
        save(img, f"icon_ticks_{opt}")

    labels = {"none": "なし", "steps": "歩数", "watchBattery": "時計", "phoneBattery": "スマホ"}
    for opt, _ in SEC_VALUES:
        img, d = canvas()
        r = k / 2 - 10 * u
        sec_col = tuple(int(RINGS["sec"][1][i:i + 2], 16) for i in (0, 2, 4))
        d.ellipse([c - r, c - r, c + r, c + r], outline=sec_col + (90,), width=int(8 * u))
        if opt != "none":
            d.arc([c - r, c - r, c + r, c + r], -90, 150, fill=sec_col + (255,), width=int(8 * u))
        size = 22 if len(labels[opt]) < 3 else 17
        try:
            font = ImageFont.truetype(font_path, int(size * u))
        except OSError:
            font = ImageFont.load_default()
        d.text((c, c), labels[opt], font=font, fill=white, anchor="mm")
        save(img, f"icon_sec_{opt}")


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
    for x1, y1, x2, y2, t in tick_lines(TICK_SETS[0][1]):  # the default set, in white
        d.line([(x1 * SS, y1 * SS), (x2 * SS, y2 * SS)], fill=(255, 255, 255, 255), width=int(t * SS))

    img = img.resize((SIZE, SIZE), Image.LANCZOS)
    angles = {"sec": 32 * 6, "min": (8 + 32 / 60) * 6, "hour": (10 + 8 / 60) * 30, "dow": (4 + 10 / 24) * 360 / 7}
    for ring, ang in angles.items():
        name = "hand_dow" if ring == "dow" else f"hand_{ring}_{HAND_DEFAULT[ring].lower()}"
        marker = Image.open(RES / "drawable-nodpi" / f"{name}.png")
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
    for ring, shapes in HAND_SHAPES.items():
        for shape in shapes:
            marker_png(ring, shape)
    marker_png("dow", "bar")
    option_icons()
    preview_png()


if __name__ == "__main__":
    main()
