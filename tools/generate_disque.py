#!/usr/bin/env python3
"""Generates the Rings Disque watch face.

Disque is the mechanical-watch take on Rings: the five rings become discs
that turn under a fixed window at 12 o'clock, so whatever sits under the
window is now and the coming hours and days read clockwise from it. It reads
the same companion data as Rings (wear/.../Rings.kt) and the same holidays,
so it only changes how they are drawn.

    python3 tools/generate_disque.py

Outputs:
    disque/src/main/res/raw/watchface.xml
    disque/src/main/res/drawable-nodpi/wx_*.png, min_mark*.png, preview.png

Everything else is drawn with PartDraw and PartText, so the face needs only
a few small images. The disc numerals use Cormorant Garamond (SIL OFL,
disque/src/main/res/font/cormorant_bold.ttf, a Latin subset of the 700
weight). The disc lettering can also be set in Cormorant with lining
figures, Cinzel or Jost (all SIL OFL, licences in disque/FONT_LICENSES/).

Options in the watch face editor: the disc lettering font, how the seconds
disc moves (one step a second, eight steps a second, or not at all), the
size of the minute numerals, and marks at 00/15/30/45 on the minute disc.
"""

import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_watchface as rings  # noqa: E402  holidays and the companion's packing

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "disque" / "src" / "main" / "res"

SIZE = 450
C = SIZE / 2
HW = 11.5  # half the width of a disc's band

# Discs from the outside in, as in Rings: radius of the band's centre line.
R = {"sec": 207.0, "min": 180.5, "hour": 154.0, "week": 127.5, "dow": 101.0}
FLANGE_R = 223.0
CENTER_R = 89.5
MOON = (C, 221.0)  # centre of the moon aperture and the gauge above it
MOON_R = 32.0

# Colours (ARGB)
INK = "FF2A2622"
MUTED = "FF6E6452"
FLANGE = "FFD8CFB9"
BAND_A = "FFF1EBDD"
BAND_B = "FFE3D9C3"
OPAL = "FFECE5D5"
GOLD = "FFC9A050"
NAVY = "FF24396A"
BURGUNDY = "FF6E1E2B"
RED = "FFB3262E"
BLUE = "FF2A4F9A"
GREEN = "FF2F6B45"
HAIR = "FF9C2A22"
LENS = "40FFFFFF"
NIGHT = "FF18264D"
MOON_GOLD = "FFE2BC62"
# Ambient: black dial, grey print, lume for what is coming up.
LUME = "FF9FDCC4"
AMB_INK = "FFB4B8BE"
AMB_LINE = "FF55595F"
AMB_RED = "FFA05A55"
AMB_BLUE = "FF566D9C"
AMB_GREEN = "FF4F7A62"

BANDS = {"sec": BAND_A, "min": BAND_B, "hour": BAND_A, "week": BAND_B, "dow": BAND_A}
FONT = "cormorant_bold"
SEG = 360 / 7

# Lettering on the discs, chosen in the editor: (id, font resource, height of
# a digit and of a capital per pixel of font size). Classic keeps the sizes in
# CLASSIC_SIZE because its old-style figures do not line up with the capitals;
# the others are sized so their letters reach the heights in LETTER_HEIGHT.
FONTS = (
    ("classic", "cormorant_bold", None, None),
    ("lining", "cormorant_lining", 0.66, 0.64),
    ("cinzel", "cinzel_bold", 0.72, 0.70),
    ("jost", "jost_semibold", 0.73, 0.70),
)
CLASSIC_SIZE = {"sec": 16, "min": 20, "minLarge": 24, "minQuarter": 26, "minSmall": 18, "hour": 18, "dow": 17}
LETTER_HEIGHT = {"sec": 11, "min": 12.5, "minLarge": 14.5, "minQuarter": 15.5, "minSmall": 11, "hour": 12,
                 "dow": 11.5}
CAPITALS = ("hour", "dow")  # roles set in capitals; the rest are digits

# Minute numerals, chosen in the editor: the size role of each numeral 0-11.
MIN_SIZES = (
    ("normal", ("min",) * 12),
    ("large", ("minLarge",) * 12),
    ("quarters", tuple("minQuarter" if i % 3 == 0 else "minSmall" for i in range(12))),
)

# How far each disc turns so that now sits under the window. The seconds
# disc moves in eighths of a second, like a 28,800 vph movement.
TURN = {
    "sec": "-(floor([SECOND_MILLISECOND] * 8) / 8) * 6",
    "min": "-[MINUTE_SECOND] * 6",
    "hour": "-[HOUR_0_11_MINUTE] * 30",
    "dow": "-(([DAY_OF_WEEK] - 1) + [HOUR_0_23_MINUTE] / 24) * 360 / 7",
}
TURN["week"] = TURN["dow"]

# How the seconds disc moves, chosen in the editor. Eight steps a second looks
# like a mechanical movement but makes the watch redraw continuously.
SEC_MOTION = (
    ("tick", "-[SECOND] * 6"),
    ("beat", TURN["sec"]),
    ("off", None),
)

FULL = f'x="0" y="0" width="{SIZE}" height="{SIZE}"'
HIDE_IN_AMBIENT = '<Variant mode="AMBIENT" target="alpha" value="0"/>'
SHOW_IN_AMBIENT = '<Variant mode="AMBIENT" target="alpha" value="255"/>'

# Weather conditions (0-15) grouped into five icons, as Rings groups them into colours.
WEATHER_ICONS = (
    ("sun", (1, 8, 14)),
    ("cloud", (2, 3, 13)),
    ("rain", (4, 6, 12)),
    ("snow", (5, 7, 10, 11)),
    ("storm", (9, 15)),
)
HOURLY = 8  # hours of forecast on the hour disc, from the current hour
DAILY = 7  # days of forecast on the weekday disc, from today

DOW_NAMES = ("SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT")
DOW_LETTERS = ("S", "M", "T", "W", "T", "F", "S")
MONTHS = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN", "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
ROMAN = ("XII", "I", "II", "III", "IIII", "V", "VI", "VII", "VIII", "IX", "X", "XI")


# ---------------------------------------------------------------- XML helpers

def point(angle, r, cx=C, cy=C):
    a = math.radians(angle)
    return cx + r * math.sin(a), cy - r * math.cos(a)


def mode_parts(mode):
    """(alpha attribute, variant) for a part shown in both modes, only the
    active one, or only ambient."""
    return {"both": ("", ""), "active": ("", HIDE_IN_AMBIENT), "ambient": (' alpha="0"', SHOW_IN_AMBIENT)}[mode]


def group(name, body, turn=None, angle=None, mode="both", box=FULL):
    alpha, variant = mode_parts(mode)
    ang = f' angle="{angle:.2f}"' if angle is not None else ""
    tr = f'<Transform target="angle" value="{turn}"/>' if turn else ""
    return (f'<Group name="{name}" {box} pivotX="0.5" pivotY="0.5"{ang}{alpha}>'
            f"{tr}{variant}{body}</Group>")


def draw(name, body, mode="both", box=FULL):
    alpha, variant = mode_parts(mode)
    return f'<PartDraw name="{name}" {box}{alpha}>{variant}{body}</PartDraw>'


def arc(r, a0, a1, color, width, cx=C, cy=C):
    return (f'<Arc centerX="{cx}" centerY="{cy}" width="{2 * r}" height="{2 * r}" '
            f'startAngle="{a0:.2f}" endAngle="{a1:.2f}">'
            f'<Stroke color="#{color}" thickness="{width}" cap="BUTT"/></Arc>')


def circle(r, color, width, cx=C, cy=C):
    return arc(r, 0, 360, color, width, cx, cy)


def disc_fill(r, color, cx=C, cy=C):
    return (f'<Ellipse x="{cx - r}" y="{cy - r}" width="{2 * r}" height="{2 * r}">'
            f'<Fill color="#{color}"/></Ellipse>')


def line(x1, y1, x2, y2, color, width, cap="BUTT"):
    return (f'<Line startX="{x1:.2f}" startY="{y1:.2f}" endX="{x2:.2f}" endY="{y2:.2f}">'
            f'<Stroke color="#{color}" thickness="{width}" cap="{cap}"/></Line>')


def radial_ticks(r1, r2, n, color, width, skip=0, cx=C, cy=C, a0=0.0, span=360.0, closed=True):
    out = []
    count = n if closed else n + 1
    for i in range(count):
        if skip and i % skip == 0:
            continue
        a = a0 + i * span / n
        x1, y1 = point(a, r1, cx, cy)
        x2, y2 = point(a, r2, cx, cy)
        out.append(line(x1, y1, x2, y2, color, width))
    return "".join(out)


def text(name, x, y, w, h, size, color, content, family=FONT, align="CENTER", spacing=None,
         weight="NORMAL", mode="both"):
    alpha, variant = mode_parts(mode)
    sp = f' letterSpacing="{spacing}"' if spacing else ""
    return (f'<PartText name="{name}" x="{round(x)}" y="{round(y)}" width="{round(w)}" height="{round(h)}"{alpha}>{variant}'
            f'<Text align="{align}" ellipsis="TRUE">'
            f'<Font family="{family}" size="{size}" weight="{weight}" color="#{color}"{sp}>'
            f"{content}</Font></Text></PartText>")


def template(fmt, *exprs):
    return "<Template>" + fmt + "".join(f'<Parameter expression="{e}"/>' for e in exprs) + "</Template>"


def on_disc(name, angle, r, w, h, size, color, content, mode="both", spacing=None, family=FONT):
    """Text centred at radius r on the disc's angle, upright when it is at 12."""
    return group(name, text(f"{name}T", C - w / 2, C - r - h / 2, w, h, size, color, content,
                            spacing=spacing, family=family), angle=angle, mode=mode)


_measure = {}


def lettering(font, role, content):
    """(size, box width, box height) for content in a font and size role."""
    _, res, digit, capital = font
    if digit is None:
        size = CLASSIC_SIZE[role]
    else:
        size = round(LETTER_HEIGHT[role] / (capital if role in CAPITALS else digit), 1)
    if res not in _measure:
        _measure[res] = ImageFont.truetype(str(RES / "font" / f"{res}.ttf"), 100)
    width = _measure[res].getlength(content) * size / 100
    return size, math.ceil(width * 1.2) + 6, math.ceil(size * 1.3)


def condition(name, expr, body, default=""):
    d = f"<Default>{default}</Default>" if default else ""
    return (f'<Condition><Expressions><Expression name="{name}"><![CDATA[{expr}]]></Expression>'
            f'</Expressions><Compare expression="{name}">{body}</Compare>{d}</Condition>')


def choose(prefix, cases, default=""):
    """One Condition with a Compare per (suffix, expression, body)."""
    exprs = "".join(f'<Expression name="{prefix}{s}"><![CDATA[{e}]]></Expression>' for s, e, _ in cases)
    compares = "".join(f'<Compare expression="{prefix}{s}">{b}</Compare>' for s, _, b in cases)
    d = f"<Default>{default}</Default>" if default else ""
    return f"<Condition><Expressions>{exprs}</Expressions>{compares}{d}</Condition>"


def lit(name, r, a0, a1, color, width, ambient=LUME, ambient_alpha=150):
    """A lit segment: its colour on the dial, lume in ambient."""
    return (draw(name, arc(r, a0, a1, color, width), mode="active")
            + f'<PartDraw name="{name}A" {FULL} alpha="0">'
            f'<Variant mode="AMBIENT" target="alpha" value="{ambient_alpha}"/>'
            f"{arc(r, a0, a1, ambient, width)}</PartDraw>")


# ---------------------------------------------------------------- the dial

# Where events sit on each disc: (radius, width).
MIN_EVENT = (R["min"] + HW - 2.75, 5.5)
HOUR_EVENT = (R["hour"] + HW - 2.75, 5.5)
WEEK_EVENT = (R["week"], 2 * HW - 2)
DAY_MARK = (R["dow"] + HW - 2.25, 4.5)  # weekends, holidays, days off, all-day events


def dial_edges():
    return [R["sec"] + HW] + [(R[a] - HW + R[b] + HW) / 2 for a, b in
                              (("sec", "min"), ("min", "hour"), ("hour", "week"), ("week", "dow"))] + [CENTER_R]


def dial():
    edges = dial_edges()
    face = (disc_fill(FLANGE_R, FLANGE)
            + "".join(circle(R[k], BANDS[k], 2 * HW) for k in R)
            + disc_fill(CENTER_R, OPAL))
    seps = "".join(circle(r, INK, 0.7) for r in edges)
    amb_seps = "".join(circle(r, AMB_LINE, 1.2) for r in edges)
    flange = radial_ticks(FLANGE_R, R["sec"] + HW + 0.5, 120, INK, 0.6)
    return (draw("face", face, mode="active")
            + draw("separators", seps, mode="active")
            + draw("flangeTicks", flange, mode="active")
            + draw("separatorsAmbient", amb_seps, mode="ambient"))


def hour_dividers(r, ink):
    """Dividers between the hours, heavier at 3, 6 and 9 and heaviest at 12."""
    out = []
    for i in range(12):
        width = 3.2 if i == 0 else 2.0 if i % 3 == 0 else 0.9
        x1, y1 = point(i * 30, r + HW)
        x2, y2 = point(i * 30, r - HW)
        out.append(line(x1, y1, x2, y2, ink, width))
    return "".join(out)


def disc_print(ink, mode, font):
    """The printing on the discs (numerals, labels, dividers), turned with them."""
    fid, res = font[0], font[1]
    tag = f"{mode}{fid}"
    out = []

    def label(name, angle, r, role, content):
        size, w, h = lettering(font, role, content)
        return on_disc(name, angle, r, w, h, size, ink, content, family=res)

    if mode == "active":  # the seconds disc stays out of ambient
        r = R["sec"]
        body = draw(f"secTicks{fid}", radial_ticks(r + HW, r + HW - 3, 60, ink, 0.9, skip=5))
        body += "".join(label(f"sec{fid}{i}", i * 30, r - 0.5, "sec", f"{i * 5:02d}") for i in range(12))
        options = "".join(
            f'<ListOption id="{opt}">'
            + (group(f"secDisc{fid}{opt}", body, turn=turn) if turn else rings.empty())
            + "</ListOption>" for opt, turn in SEC_MOTION)
        out.append(group(f"secDisc{fid}", f'<ListConfiguration id="secMotion">{options}</ListConfiguration>',
                         mode=mode))

    r = R["min"]
    sizes = "".join(
        f'<ListOption id="{opt}">'
        + group(f"minNum{tag}{opt}", "".join(label(f"min{tag}{opt}{i}", i * 30, r - 3, role, f"{i * 5:02d}")
                                             for i, role in enumerate(roles)))
        + "</ListOption>" for opt, roles in MIN_SIZES)
    body = (draw(f"minTicks{tag}", radial_ticks(r - HW, r - HW + 2.8, 60, ink, 0.7, skip=5))
            + f'<ListConfiguration id="minSize">{sizes}</ListConfiguration>')
    out.append(group(f"minDisc{tag}", body, turn=TURN["min"], mode=mode))

    r = R["hour"]
    body = draw(f"hourTicks{tag}", hour_dividers(r, ink))
    body += "".join(label(f"hour{tag}{i}", i * 30 + 8.5, r - 3, "hour", ROMAN[i]) for i in range(12))
    out.append(group(f"hourDisc{tag}", body, turn=TURN["hour"], mode=mode))

    r = R["week"]
    body = draw(f"weekTicks{tag}", radial_ticks(r + HW, r - HW, 7, ink, 0.8)
                + radial_ticks(r - HW, r - HW + 2.8, 84, ink, 0.7, skip=12))
    out.append(group(f"weekDisc{tag}", body, turn=TURN["week"], mode=mode))

    r = R["dow"]
    body = draw(f"dowTicks{tag}", radial_ticks(r + HW, r - HW, 7, ink, 0.9))
    body += "".join(label(f"dow{tag}{i}", (i + 0.5) * SEG - 9, r - 2.5, "dow", DOW_LETTERS[i]) for i in range(7))
    out.append(group(f"dowDisc{tag}", body, turn=TURN["dow"], mode=mode))
    return "".join(out)


def disc_lettering():
    """disc_print in each font, under the font option."""
    options = "".join(
        f'<ListOption id="{font[0]}">'
        + group(f"lettering{font[0]}", disc_print(INK, "active", font) + disc_print(AMB_INK, "ambient", font))
        + "</ListOption>" for font in FONTS)
    return f'<ListConfiguration id="discFont">{options}</ListConfiguration>'


def minute_marks():
    """An inward triangle at 00 and short lines at 15, 30 and 45 on the minute
    disc's outer edge, drawn over the events; switched in the editor."""
    r = R["min"] + HW
    lines = "".join(line(*point(a, r), *point(a, r - 5.5), INK, 1.8) for a in (90, 180, 270))
    lines_amb = "".join(line(*point(a, r), *point(a, r - 5.5), LUME, 1.8) for a in (90, 180, 270))
    tri = lambda name, res, alpha: (f'<PartImage name="{name}" x="{round(C - 5)}" y="{round(C - r)}" width="10" '
                                    f'height="8"{alpha}><Image resource="{res}"/>'
                                    + (SHOW_IN_AMBIENT if alpha else HIDE_IN_AMBIENT) + "</PartImage>")
    body = (draw("minMarkLines", lines, mode="active") + draw("minMarkLinesAmb", lines_amb, mode="ambient")
            + tri("minMarkTop", "min_mark", "") + tri("minMarkTopAmb", "min_mark_amb", ' alpha="0"'))
    return ('<BooleanConfiguration id="minMarks">'
            f'<BooleanOption id="TRUE">{group("minMarks", body, turn=TURN["min"])}</BooleanOption>'
            f'<BooleanOption id="FALSE">{rings.empty()}</BooleanOption>'
            "</BooleanConfiguration>")


def user_configurations():
    def options(ids, prefix):
        return "".join(f'<ListOption id="{i}" displayName="@string/{prefix}_{i}"/>' for i in ids)

    return ("<UserConfigurations>"
            '<ListConfiguration id="discFont" displayName="@string/cfg_disc_font" defaultValue="classic">'
            + options([f[0] for f in FONTS], "font") + "</ListConfiguration>"
            '<ListConfiguration id="minSize" displayName="@string/cfg_min_size" defaultValue="normal">'
            + options([m[0] for m in MIN_SIZES], "min_size") + "</ListConfiguration>"
            '<BooleanConfiguration id="minMarks" displayName="@string/cfg_min_marks" defaultValue="FALSE"/>'
            '<ListConfiguration id="secMotion" displayName="@string/cfg_sec_motion" defaultValue="tick">'
            + options([m[0] for m in SEC_MOTION], "sec_motion") + "</ListConfiguration>"
            "</UserConfigurations>")


def day_marks():
    """Sundays and Saturdays always, holidays from a week before, on the weekday disc."""
    r, w = DAY_MARK
    body = (lit("sunday", r, 0, SEG, RED, w, AMB_RED, 255)
            + lit("saturday", r, 6 * SEG, 360, BLUE, w, AMB_BLUE, 255))
    by_index = {i: [] for i in range(7)}
    for year in rings.HOLIDAY_YEARS:
        for d in rings.japanese_holidays(year):
            idx = rings.ring_index(d)
            if idx:
                lo = d - rings.dt.timedelta(days=6)
                by_index[idx].append((int(lo.strftime("%Y%m%d")), int(d.strftime("%Y%m%d"))))
    for idx, ranges in by_index.items():
        if ranges:
            terms = " || ".join(f"({rings.DATE_NUM} >= {lo} && {hi} >= {rings.DATE_NUM})" for lo, hi in ranges)
            body += condition(f"holiday{idx}", terms, lit(f"holiday{idx}", r, idx * SEG, (idx + 1) * SEG,
                                                            RED, w, AMB_RED, 255))
    return group("dayMarks", body, turn=TURN["dow"])


# ---------------------------------------------------------------- companion data

V = rings.V
T = rings.T


def data_slot(slot_id, name, source, body):
    """As in Rings: a full-face slot fixed to one of the companion's sources.
    Keep the slot order once people use the face (see generate_watchface.py)."""
    return (f'<ComplicationSlot slotId="{slot_id}" name="{name}" displayName="@string/{name}" '
            f'{FULL} supportedTypes="GOAL_PROGRESS" isCustomizable="FALSE">'
            f'<DefaultProviderPolicy defaultSystemProvider="EMPTY" defaultSystemProviderType="GOAL_PROGRESS" '
            f'primaryProvider="{rings.COMPANION}{source}" primaryProviderType="GOAL_PROGRESS"/>'
            f'<BoundingBox {FULL}/>'
            f'<Complication type="GOAL_PROGRESS">{body}</Complication></ComplicationSlot>')


def bit(field, i):
    return rings.bit(field, i)


def minute_segments(prefix, field, shift, ks):
    r, w = MIN_EVENT
    return "".join(condition(f"{prefix}{k}", bit(field, k - shift),
                             lit(f"{prefix}Seg{k}", r, k * 6, (k + 1) * 6, NAVY, w)) for k in ks)


def week_day(day, field, shift, offset=""):
    r, w = WEEK_EVENT
    block = SEG / 12
    return "".join(condition(f"week{day}b{b}", bit(f"({field}{offset})", shift + b),
                             lit(f"week{day}s{b}", r, day * SEG + b * block, day * SEG + (b + 1) * block,
                                 BURGUNDY, w, ambient_alpha=110))
                   for b in range(12))


def gauge_parts(battery, valid):
    """The phone's battery as a power-reserve gauge above the moon, -70 to +70 degrees."""
    cx, cy = MOON
    angle = f"-70 + ({battery}) * 1.4"
    fill = (f'<PartDraw name="gaugeFill" {FULL}>{HIDE_IN_AMBIENT}'
            f'<Arc centerX="{cx}" centerY="{cy}" width="93" height="93" startAngle="-70" endAngle="-70">'
            f'<Stroke color="#{GOLD}" thickness="3" cap="BUTT"/>'
            f'<Transform target="endAngle" value="{angle}"/></Arc></PartDraw>')
    box = f'x="{round(cx - 60)}" y="{round(cy - 60)}" width="120" height="120"'
    marker = group("gaugeMarker", draw("gaugeMarkerLine", line(60, 60 - 35.5, 60, 60 - 41, NAVY, 2.6, "ROUND"))
                   + f'<PartDraw name="gaugeMarkerAmb" x="0" y="0" width="120" height="120" alpha="0">'
                   f"{SHOW_IN_AMBIENT}{line(60, 60 - 35.5, 60, 60 - 41, LUME, 2.6, 'ROUND')}</PartDraw>",
                   turn=angle, box=box)
    label = (text("gaugeLabel", cx - 50, 156, 100, 16, 12, MUTED, template("phone %d", battery),
                  spacing=0.08, mode="active")
             + text("gaugeLabelAmb", cx - 50, 156, 100, 16, 12, AMB_INK, template("phone %d", battery),
                    spacing=0.08, mode="ambient"))
    return condition("phoneValid", valid, fill + marker + label)


def companion_slots():
    r, w = HOUR_EVENT
    hour = "".join(condition(f"hourBit{i}", bit(V, i), lit(f"hourSeg{i}", r, i * 30, (i + 1) * 30, NAVY, w))
                   for i in range(12))
    hour_slot = (group("hourEvents", hour, turn=TURN["hour"])
                 + group("minEventsLow", minute_segments("minLo", f"({T} - 1)", 0, range(24)), turn=TURN["min"]))

    week_a = week_day(0, V, 0) + week_day(1, V, 12) + week_day(2, T, 0, " - 1") + week_day(3, T, 12, " - 1")
    week_b = week_day(4, V, 0) + week_day(5, V, 12) + week_day(6, T, 0, " - 1")

    mr, mw = DAY_MARK
    all_day_b = "".join(condition(f"allDay{d}", bit(f"({T} - 1)", 19 + d),
                                  lit(f"allDay{d}", mr, d * SEG, (d + 1) * SEG, GREEN, mw, AMB_GREEN, 255))
                        for d in range(5))
    all_day_m = "".join(condition(f"allDay{d}", bit(f"({T} - 1)", 20 + d - 5),
                                  lit(f"allDay{d}", mr, d * SEG, (d + 1) * SEG, GREEN, mw, AMB_GREEN, 255))
                        for d in range(5, 7))
    days_off = "".join(condition(f"dayOff{d}", bit(f"({T} - 1)", 12 + d),
                                 lit(f"dayOff{d}", mr, d * SEG, (d + 1) * SEG, RED, mw, AMB_RED, 255))
                       for d in range(7))

    minutes_high = (minute_segments("minHi", V, 24, range(24, 48))
                    + minute_segments("minTop", f"({T} - 1)", 48, range(48, 60)))
    battery = f"(floor(({T} - 1) / 4096) % 128)"
    minute_slot = (group("minEventsHigh", minutes_high, turn=TURN["min"])
                   + group("allDayLate", all_day_m, turn=TURN["dow"])
                   + gauge_parts(battery, bit(f"({T} - 1)", 19)))

    return (data_slot(1, "ring_hour", "HourRingDataSource", hour_slot)
            + data_slot(2, "ring_week_a", "WeekADataSource", group("weekA", week_a, turn=TURN["week"]))
            + data_slot(3, "ring_week_b", "WeekBDataSource",
                        group("weekB", week_b, turn=TURN["week"])
                        + group("dayFlags", all_day_b + days_off, turn=TURN["dow"]))
            + data_slot(4, "ring_minute", "MinuteRingDataSource", minute_slot))


# ---------------------------------------------------------------- weather

ICON = 20  # icon size on the face


def weather_icon(prefix, avail, cond, angle, r, suffix=""):
    """The icon for a forecast, centred at radius r and the given angle from 12.
    suffix picks the image set: "" in colour, "_amb" in grey for ambient."""
    img = lambda kind: (f'<PartImage name="{prefix}{kind}" x="{round(C - ICON / 2)}" y="{round(C - r - ICON / 2)}" '
                        f'width="{ICON}" height="{ICON}"><Image resource="wx_{kind}{suffix}"/></PartImage>')
    cases = [(kind, f"{avail} && (" + " || ".join(f"{cond} == {v}" for v in values) + ")", img(kind))
             for kind, values in WEATHER_ICONS]
    return group(f"{prefix}Icon", choose(prefix, cases), angle=angle)


def forecasts():
    """Icons in colour on the dial and in grey in ambient mode."""
    out = []
    for mode, sfx, img in (("active", "", ""), ("ambient", "A", "_amb")):
        r = R["hour"] - 3
        for k in range(HOURLY):
            avail = f"[WEATHER.HOURS.{k}.IS_AVAILABLE]"
            # The hour starting k hours after this one, relative to the window.
            turn = f"{k * 30} - ([MINUTE_SECOND]) * 0.5"
            body = weather_icon(f"wxH{sfx}{k}", avail, f"[WEATHER.HOURS.{k}.CONDITION]", 23, r, img)
            out.append(group(f"wxHour{sfx}{k}", condition(f"wxH{sfx}{k}On", avail, body), turn=turn, mode=mode))
        r = R["dow"] - 2.5
        for d in range(DAILY):
            avail = f"[WEATHER.DAYS.{d}.IS_AVAILABLE]"
            turn = f"({d} + 0.5) * {SEG:.4f} - [HOUR_0_23_MINUTE] / 24 * {SEG:.4f}"
            body = weather_icon(f"wxD{sfx}{d}", avail, f"[WEATHER.DAYS.{d}.CONDITION_DAY]", 9, r, img)
            out.append(group(f"wxDay{sfx}{d}", condition(f"wxD{sfx}{d}On", avail, body), turn=turn, mode=mode))
    return "".join(out)


# ---------------------------------------------------------------- centre

def moon():
    """Moon phase: a night-blue disc with two moons turning half a turn per
    lunation, seen through a window with two humps, as on a mechanical watch."""
    cx, cy = MOON
    box = f'x="{round(cx - 40)}" y="{round(cy - 40)}" width="80" height="80"'
    moons = draw("moons", disc_fill(11.25, MOON_GOLD, 24, 40) + disc_fill(11.25, MOON_GOLD, 56, 40)
                 + disc_fill(0.9, MOON_GOLD, 40, 20) + disc_fill(0.7, MOON_GOLD, 50, 28)
                 + disc_fill(0.9, MOON_GOLD, 30, 54) + disc_fill(0.7, MOON_GOLD, 46, 60),
                 box='x="0" y="0" width="80" height="80"')
    cover = (f'<Rectangle x="{cx - 40}" y="{cy}" width="80" height="40"><Fill color="#{OPAL}"/></Rectangle>'
             + disc_fill(16, OPAL, cx - 16, cy) + disc_fill(16, OPAL, cx + 16, cy))
    frame = (f'<Arc centerX="{cx}" centerY="{cy}" width="{2 * MOON_R}" height="{2 * MOON_R}" '
             f'startAngle="-90" endAngle="90"><Stroke color="#{GOLD}" thickness="1.5" cap="BUTT"/></Arc>'
             + line(cx - 38, cy, cx + 38, cy, GOLD, 1.1))
    # The full moon is at the top when MOON_PHASE_POSITION is half way through its 0-27 cycle.
    return group("moon", draw("night", disc_fill(MOON_R + 2, NIGHT))
                 + group("moonDisc", moons, turn="[MOON_PHASE_POSITION] / 28 * 180", box=box)
                 + draw("moonCover", cover) + draw("moonFrame", frame), mode="active")


def gauge_static():
    cx, cy = MOON
    track = (f'<Arc centerX="{cx}" centerY="{cy}" width="93" height="93" startAngle="-70" endAngle="70">'
             f'<Stroke color="#FFD2C6AB" thickness="3" cap="BUTT"/></Arc>')
    ticks = "".join(
        line(*point(-70 + 14 * i, 45, cx, cy), *point(-70 + 14 * i, 45 - (2.8 if i % 5 == 0 else 1.7), cx, cy),
             INK, 0.7) for i in range(1, 10))
    # Empty and full stand out on the dial and stay lit in ambient mode.
    ends = lambda color: "".join(line(*point(a, 49.5, cx, cy), *point(a, 41, cx, cy), color, 2.2, "ROUND")
                                 for a in (-70, 70))
    return (draw("gauge", track + ticks + ends(GOLD), mode="active")
            + draw("gaugeEndsAmb", ends(LUME), mode="ambient"))


def centre():
    rings_logo = (text("logo", C - 60, 140, 120, 20, 17, INK, "RINGS", spacing=0.35, mode="active")
                  + text("logoAmb", C - 60, 140, 120, 20, 17, AMB_INK, "RINGS", spacing=0.35, mode="ambient"))

    def weather_text(color, mode, sfx):
        return condition(f"weather{sfx}", "[WEATHER.IS_AVAILABLE] && !([WEATHER.IS_ERROR])",
                         text(f"weatherText{sfx}", C - 75, 254, 150, 22, 16, color,
                              template("%d° %s", "[WEATHER.TEMPERATURE]", "[WEATHER.CONDITION_NAME]"),
                              family="SYNC_TO_DEVICE", mode=mode),
                         text(f"weatherNone{sfx}", C - 75, 254, 150, 22, 16, color, "--°",
                              family="SYNC_TO_DEVICE", mode=mode))

    def date(color, mode, sfx):
        dow = choose(f"dateDow{sfx}", [(str(i), f"[DAY_OF_WEEK] == {i + 1}",
                                        text(f"dateDow{sfx}{i}", C - 66, 276, 62, 18, 14, color, name,
                                             align="END", spacing=0.12, mode=mode))
                                       for i, name in enumerate(DOW_NAMES)])
        month = choose(f"dateMon{sfx}", [(str(i), f"[MONTH] == {i + 1}",
                                          text(f"dateMon{sfx}{i}", C + 4, 276, 66, 18, 14, color,
                                               template(f"{name} %d", "[DAY]"), align="START", spacing=0.12,
                                               mode=mode))
                                         for i, name in enumerate(MONTHS)])
        return dow + month

    return (moon() + gauge_static() + rings_logo
            + weather_text(INK, "active", "") + weather_text(AMB_INK, "ambient", "Amb")
            + date(MUTED, "active", "") + date(AMB_INK, "ambient", "Amb"))


def next_event():
    event = template("%s %s", "[COMPLICATION.TITLE]", "[COMPLICATION.TEXT]")
    return ('<ComplicationSlot slotId="0" name="nextEvent" displayName="@string/next_event" '
            'x="137" y="229" width="176" height="26" supportedTypes="LONG_TEXT" isCustomizable="TRUE">'
            '<DefaultProviderPolicy defaultSystemProvider="NEXT_EVENT" defaultSystemProviderType="LONG_TEXT"/>'
            '<BoundingBox x="0" y="0" width="176" height="26"/>'
            '<Complication type="LONG_TEXT">'
            + text("eventLong", 0, 0, 176, 26, 16, NAVY, event, family="SYNC_TO_DEVICE", weight="BOLD",
                   mode="active")
            + text("eventLongAmb", 0, 0, 176, 26, 16, LUME, event, family="SYNC_TO_DEVICE", weight="BOLD",
                   mode="ambient")
            + "</Complication></ComplicationSlot>")


def index_window():
    x, y0, y1, w = C - 12, 3.0, 138.0, 24
    lens = (f'<RoundRectangle x="{x}" y="{y0}" width="{w}" height="{y1 - y0}" cornerRadiusX="3.5" '
            f'cornerRadiusY="3.5"><Fill color="#{LENS}"/><Stroke color="#{GOLD}" thickness="1.7"/></RoundRectangle>'
            + line(C, y0 + 3, C, y1 - 3, HAIR, 0.8))
    lens_amb = (f'<RoundRectangle x="{x}" y="{y0}" width="{w}" height="{y1 - y0}" cornerRadiusX="3.5" '
                f'cornerRadiusY="3.5"><Stroke color="#{LUME}" thickness="1.7"/></RoundRectangle>'
                + line(C, y0 + 3, C, y1 - 3, LUME, 0.8))
    return draw("lens", lens, mode="active") + draw("lensAmb", lens_amb, mode="ambient")


def watchface_xml():
    return f"""<?xml version="1.0" encoding="utf-8"?>
<!-- Generated by tools/generate_disque.py. Edit the script, not this file. -->
<WatchFace width="{SIZE}" height="{SIZE}" clipShape="CIRCLE">
  <Metadata key="CLOCK_TYPE" value="ANALOG"/>
  <Metadata key="PREVIEW_TIME" value="10:08:32"/>
  {user_configurations()}
  <Scene backgroundColor="#FF000000">
    {dial()}
    {disc_lettering()}
    {day_marks()}
    {companion_slots()}
    {minute_marks()}
    {forecasts()}
    {centre()}
    {next_event()}
    {index_window()}
  </Scene>
</WatchFace>
"""


# ---------------------------------------------------------------- images

SS = 8


def rgba(argb):
    return tuple(int(argb[i:i + 2], 16) for i in (2, 4, 6, 0))


def icons():
    out = RES / "drawable-nodpi"
    k = 48
    s = k / 12  # one face pixel
    sets = (
        ("", {"sun": "FFC08A1E", "cloud": "FF858891", "rain": "FF2F5D9E", "snow": "FF5F86B8", "bolt": "FF7A3FA0"}),
        ("_amb", {"sun": AMB_INK, "cloud": AMB_INK, "rain": AMB_INK, "snow": AMB_INK, "bolt": AMB_INK}),
    )
    for suffix, colors in sets:
        def cloud(d, dy):
            col = rgba(colors["cloud"])
            for cx, cy, r in ((-2.4, 0.9, 2.3), (0.3, -0.6, 3.1), (2.8, 1.0, 2.2)):
                d.ellipse([(6 + cx - r) * s, (6 + cy + dy - r) * s, (6 + cx + r) * s, (6 + cy + dy + r) * s], fill=col)
            d.rectangle([(6 - 2.4) * s, (6 + 1 + dy) * s, (6 + 2.8) * s, (6 + 3.2 + dy) * s], fill=col)

        for kind, _ in WEATHER_ICONS:
            img = Image.new("RGBA", (k, k), (0, 0, 0, 0))
            d = ImageDraw.Draw(img)
            if kind == "sun":
                col = rgba(colors["sun"])
                d.ellipse([(6 - 2.3) * s, (6 - 2.3) * s, (6 + 2.3) * s, (6 + 2.3) * s], fill=col)
                for i in range(8):
                    a = i / 8 * 2 * math.pi
                    d.line([((6 + 3.5 * math.cos(a)) * s, (6 + 3.5 * math.sin(a)) * s),
                            ((6 + 5 * math.cos(a)) * s, (6 + 5 * math.sin(a)) * s)], fill=col, width=int(0.9 * s))
            elif kind == "cloud":
                cloud(d, 0)
            elif kind == "rain":
                cloud(d, -1.6)
                for dx in (-2, 0.4, 2.8):
                    d.line([((6 + dx) * s, 8.8 * s), ((6 + dx - 0.8) * s, 10.8 * s)], fill=rgba(colors["rain"]),
                           width=int(1 * s))
            elif kind == "snow":
                for i in range(3):
                    a = i / 3 * math.pi + math.pi / 2
                    d.line([((6 + 4 * math.cos(a)) * s, (6 + 4 * math.sin(a)) * s),
                            ((6 - 4 * math.cos(a)) * s, (6 - 4 * math.sin(a)) * s)], fill=rgba(colors["snow"]),
                           width=int(0.9 * s))
            else:
                cloud(d, -1.8)
                pts = [(0.8, 1.4), (-1.4, 4.2), (0, 4.2), (-0.8, 6.4), (1.9, 3.2), (0.4, 3.2)]
                d.polygon([((6 + x) * s, (6 + y) * s) for x, y in pts], fill=rgba(colors["bolt"]))
            img.save(out / f"wx_{kind}{suffix}.png", optimize=True)


def minute_mark_images():
    """The inward triangle at 00 on the minute disc, in ink and in lume."""
    for name, color in (("min_mark", INK), ("min_mark_amb", LUME)):
        img = Image.new("RGBA", (10 * SS, 8 * SS), (0, 0, 0, 0))
        ImageDraw.Draw(img).polygon([(0, 0), (10 * SS, 0), (5 * SS, 8 * SS)], fill=rgba(color))
        img.resize((40, 32), Image.LANCZOS).save(RES / "drawable-nodpi" / f"{name}.png", optimize=True)


def preview_png():
    """A still of the face at 10:08:32 on a Thursday, for the watch face picker."""
    k = SIZE * 2
    s = 2
    img = Image.new("RGBA", (k, k), (0, 0, 0, 255))
    font_path = RES / "font" / f"{FONT}.ttf"

    def font(size):
        return ImageFont.truetype(str(font_path), int(size * s))

    def ring(r, width, color, a0=0, a1=360):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        box = [(C - r) * s, (C - r) * s, (C + r) * s, (C + r) * s]
        ImageDraw.Draw(layer).arc(box, a0 - 90, a1 - 90, fill=rgba(color), width=max(1, int(width * s)))
        img.alpha_composite(layer)

    d = ImageDraw.Draw(img)
    d.ellipse([(C - FLANGE_R) * s] * 2 + [(C + FLANGE_R) * s] * 2, fill=rgba(FLANGE))
    for key, r in R.items():
        ring(r, 2 * HW, BANDS[key])
    d.ellipse([(C - CENTER_R) * s] * 2 + [(C + CENTER_R) * s] * 2, fill=rgba(OPAL))
    turns = {"sec": -32 * 6, "min": -(8 + 32 / 60) * 6, "hour": -(10 + 8 / 60) * 30,
             "dow": -(4 + 10.14 / 24) * SEG}
    turns["week"] = turns["dow"]

    def label(txt, angle, r, size):
        layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        ImageDraw.Draw(layer).text((C * s, (C - r) * s), txt, font=font(size), fill=rgba(INK), anchor="mm")
        img.alpha_composite(layer.rotate(-angle, resample=Image.BICUBIC, center=(C * s, C * s)))

    ring(HOUR_EVENT[0], HOUR_EVENT[1], NAVY, 14 * 30 % 360 + turns["hour"], 15 * 30 % 360 + turns["hour"])
    ring(WEEK_EVENT[0], WEEK_EVENT[1], BURGUNDY, 4 * SEG + 5 * SEG / 12 + turns["dow"],
         4 * SEG + 6 * SEG / 12 + turns["dow"])
    ring(DAY_MARK[0], DAY_MARK[1], RED, turns["dow"], SEG + turns["dow"])
    ring(DAY_MARK[0], DAY_MARK[1], BLUE, 6 * SEG + turns["dow"], 7 * SEG + turns["dow"])
    for i in range(12):
        label(f"{i * 5:02d}", i * 30 + turns["sec"], R["sec"] - 0.5, 16)
        label(f"{i * 5:02d}", i * 30 + turns["min"], R["min"] - 3, 20)
        label(ROMAN[i], i * 30 + 8.5 + turns["hour"], R["hour"] - 3, 18)
    for i in range(7):
        label(DOW_LETTERS[i], (i + 0.5) * SEG - 9 + turns["dow"], R["dow"] - 2.5, 17)
    d = ImageDraw.Draw(img)
    for key in ("hour", "week", "dow"):
        n = 12 if key == "hour" else 7
        for i in range(n):
            a = i * 360 / n + turns[key]
            p, q = point(a, R[key] + HW), point(a, R[key] - HW)
            d.line([(p[0] * s, p[1] * s), (q[0] * s, q[1] * s)], fill=rgba(INK), width=2)
    for r in dial_edges():
        ring(r, 0.7, INK)
    cx, cy = MOON
    d.pieslice([(cx - MOON_R) * s, (cy - MOON_R) * s, (cx + MOON_R) * s, (cy + MOON_R) * s], 180, 360,
               fill=rgba(NIGHT))
    d.ellipse([(cx - 11.25) * s, (cy - 16 - 11.25) * s, (cx + 11.25) * s, (cy - 16 + 11.25) * s], fill=rgba(MOON_GOLD))
    for hx in (cx - 16, cx + 16):
        d.ellipse([(hx - 16) * s, (cy - 16) * s, (hx + 16) * s, (cy + 16) * s], fill=rgba(OPAL))
    d.rectangle([(cx - 40) * s, cy * s, (cx + 40) * s, (cy + 34) * s], fill=rgba(OPAL))
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(layer).arc([(cx - 46.5) * s, (cy - 46.5) * s, (cx + 46.5) * s, (cy + 46.5) * s], -160, -20,
                              fill=rgba("FFD2C6AB"), width=3 * s)
    img.alpha_composite(layer)
    d = ImageDraw.Draw(img)
    d.text((C * s, 150 * s), "RINGS", font=font(17), fill=rgba(INK), anchor="mm")
    d.text((C * s, 285 * s), "THU  OCT 15", font=font(14), fill=rgba(MUTED), anchor="mm")
    x, y0, y1, w = C - 12, 3.0, 138.0, 24
    d.rounded_rectangle([x * s, y0 * s, (x + w) * s, y1 * s], radius=7, outline=rgba(GOLD), width=3)
    d.line([(C * s, (y0 + 3) * s), (C * s, (y1 - 3) * s)], fill=rgba(HAIR), width=1)
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).ellipse([0, 0, k - 1, k - 1], fill=255)
    out = Image.new("RGB", img.size, (0, 0, 0))
    out.paste(img, mask=mask)
    out.resize((SIZE, SIZE), Image.LANCZOS).save(RES / "drawable-nodpi" / "preview.png", optimize=True)


def main():
    for sub in ("raw", "drawable-nodpi"):
        (RES / sub).mkdir(parents=True, exist_ok=True)
    (RES / "raw" / "watchface.xml").write_text(watchface_xml(), encoding="utf-8")
    icons()
    minute_mark_images()
    preview_png()


if __name__ == "__main__":
    main()
