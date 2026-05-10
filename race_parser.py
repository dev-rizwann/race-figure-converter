from __future__ import annotations

import re
from dataclasses import dataclass, field
from io import BytesIO
from typing import Iterable

from pypdf import PdfReader


HEADING_RE = re.compile(
    r"^(?P<course>[A-Z][A-Z '\-.&]{2,})\s+"
    r"(?P<time>\d{1,2}\.\d{2})\s+"
    r"(?P<date>.+)$"
)
RUNNER_RE = re.compile(r"^(.+?)\s+(\d{1,2})\s+(\d{1,2}-\d{1,2})\s+(\d{2,3})$")
PERFORMANCE_START_RE = re.compile(r"^\d+\s+")
PERFORMANCE_END_RE = re.compile(
    r"(?P<speed>-|\d+-?)\s+"
    r"(?P<trip>r?\d+(?:\.\d+)?[A-Za-z]+)\s+"
    r"(?P<rating>-|\d+-?)\s*$"
)


@dataclass
class Runner:
    name: str
    age: int
    weight: str
    weight_lbs: int
    performance_lines: list[str] = field(default_factory=list)
    last_form_line: str = ""
    last_speed_figure: int | None = None
    figure: int | None = None


@dataclass
class Race:
    course: str
    time: str
    date: str
    title: str = ""
    details: str = ""
    runners: list[Runner] = field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.course} {self.time} {self.date}"

    @property
    def label(self) -> str:
        suffix = f" - {self.title}" if self.title else ""
        return f"{self.course} {self.time}{suffix}"


@dataclass
class ParsedRaceFile:
    source_name: str
    races: list[Race]
    warnings: list[str] = field(default_factory=list)


def clean_line(value: str) -> str:
    return " ".join(
        value.replace("\x19", "'")
        .replace("\u0141", "£")
        .replace("\ufffd", "")
        .strip()
        .split()
    )


def parse_number_token(token: str) -> int | None:
    if token == "-":
        return None
    stripped = token.rstrip("-")
    return int(stripped) if stripped.isdigit() else None


def is_heading(line: str):
    match = HEADING_RE.match(line)
    if not match:
        return None

    course = match.group("course").strip()
    date = match.group("date").strip()
    if len(course.split()) > 5 or any(char.isdigit() for char in course):
        return None
    if not re.search(r"[A-Za-z]", date):
        return None
    return match


def is_runner_line(line: str):
    match = RUNNER_RE.match(line)
    if not match:
        return None

    name = match.group(1).strip()
    words = name.split()
    if not words or any(not word[0].isalpha() or not word[0].isupper() for word in words):
        return None
    if is_heading(line):
        return None
    return match


def extract_text_lines(pdf_bytes: bytes) -> list[str]:
    reader = PdfReader(BytesIO(pdf_bytes))
    lines: list[str] = []
    for page in reader.pages:
        page_text = page.extract_text() or ""
        lines.extend(page_text.splitlines())
    return [clean_line(line) for line in lines if clean_line(line)]


def parse_performance_lines(raw_lines: Iterable[str]) -> list[str]:
    performance_lines: list[str] = []
    current: str | None = None

    for line in raw_lines:
        if not line or is_heading(line) or re.match(r"^\d+$", line):
            continue

        if line.lower().startswith("then moved"):
            if current:
                performance_lines.append(current)
                current = None
            continue

        if PERFORMANCE_START_RE.match(line):
            if current:
                performance_lines.append(current)
            current = line
            continue

        if current:
            if PERFORMANCE_END_RE.search(current):
                performance_lines.append(current)
                current = None
            else:
                current = f"{current} {line}"

    if current:
        performance_lines.append(current)

    return performance_lines


def finalize_runner(runner: Runner) -> None:
    parsed_lines = parse_performance_lines(runner.performance_lines)
    runner.performance_lines = parsed_lines
    runner.last_form_line = parsed_lines[-1] if parsed_lines else ""

    if not runner.last_form_line:
        return

    match = PERFORMANCE_END_RE.search(runner.last_form_line)
    if not match:
        return

    runner.last_speed_figure = parse_number_token(match.group("speed"))
    if runner.last_speed_figure is not None:
        runner.figure = runner.weight_lbs - runner.last_speed_figure


def parse_pdf(pdf_bytes: bytes, source_name: str = "uploaded.pdf") -> ParsedRaceFile:
    lines = extract_text_lines(pdf_bytes)
    races_by_key: dict[str, Race] = {}
    race_order: list[str] = []
    current_race: Race | None = None
    current_runner: Runner | None = None
    warnings: list[str] = []

    def ensure_race(course: str, time: str, date: str) -> Race:
        key = f"{course} {time} {date}"
        if key not in races_by_key:
            races_by_key[key] = Race(course=course, time=time, date=date)
            race_order.append(key)
        return races_by_key[key]

    def flush_runner() -> None:
        nonlocal current_runner
        if not current_runner or not current_race:
            return
        finalize_runner(current_runner)
        current_race.runners.append(current_runner)
        current_runner = None

    for line in lines:
        heading = is_heading(line)
        if heading:
            next_race = ensure_race(
                heading.group("course").strip(),
                heading.group("time"),
                heading.group("date").strip(),
            )
            if current_race and next_race.key != current_race.key:
                flush_runner()
            current_race = next_race
            continue

        runner_match = is_runner_line(line)
        if runner_match and current_race:
            flush_runner()
            current_runner = Runner(
                name=runner_match.group(1),
                age=int(runner_match.group(2)),
                weight=runner_match.group(3),
                weight_lbs=int(runner_match.group(4)),
            )
            continue

        if current_runner:
            current_runner.performance_lines.append(line)
            continue

        if current_race and not re.match(r"^\d+$", line):
            if not current_race.title:
                current_race.title = line
            elif not current_race.details and line != current_race.title:
                current_race.details = line

    flush_runner()

    races = [races_by_key[key] for key in race_order if races_by_key[key].runners]

    if not lines:
        warnings.append("No selectable text was found in the PDF. It may be a scanned image.")
    if not races:
        warnings.append("No race runner tables were detected.")
    for race in races:
        missing = [runner.name for runner in race.runners if runner.last_speed_figure is None]
        if missing:
            warnings.append(
                f"{race.course} {race.time}: {len(missing)} runner(s) have no usable last speed figure."
            )

    return ParsedRaceFile(source_name=source_name, races=races, warnings=warnings)
