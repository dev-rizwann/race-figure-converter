from __future__ import annotations

from io import BytesIO
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.page import PageMargins

from race_parser import ParsedRaceFile, Race, Runner


TITLE_FILL = "173B45"
RACE_FILL = "2E6F7E"
HEADER_FILL = "DCECEF"
TEXT = "1F2933"
WHITE = "FFFFFF"


def sorted_runners(runners: list[Runner]) -> list[Runner]:
    return sorted(
        runners,
        key=lambda runner: (
            runner.figure is None,
            runner.figure if runner.figure is not None else 10_000,
            runner.name,
        ),
    )


def write_race_table(ws, race: Race, start_row: int, start_col: int) -> int:
    runners = sorted_runners(race.runners)
    end_col = start_col + 3

    ws.merge_cells(
        start_row=start_row,
        start_column=start_col,
        end_row=start_row,
        end_column=end_col,
    )
    title_cell = ws.cell(start_row, start_col)
    title_cell.value = race.label
    title_cell.fill = PatternFill("solid", fgColor=RACE_FILL)
    title_cell.font = Font(bold=True, color=WHITE)
    title_cell.alignment = Alignment(vertical="center")

    headers = ["Runner", "Weight lbs", "Last Speed", "Figure"]
    for idx, header in enumerate(headers):
        cell = ws.cell(start_row + 1, start_col + idx)
        cell.value = header
        cell.fill = PatternFill("solid", fgColor=HEADER_FILL)
        cell.font = Font(bold=True, color=TITLE_FILL)
        cell.alignment = Alignment(vertical="center")

    for row_offset, runner in enumerate(runners, start=2):
        row = start_row + row_offset
        values = [
            runner.name,
            runner.weight_lbs,
            runner.last_speed_figure,
            runner.figure,
        ]
        for col_offset, value in enumerate(values):
            cell = ws.cell(row, start_col + col_offset)
            cell.value = value
            cell.font = Font(color=TEXT)
            cell.alignment = Alignment(vertical="top")

    return len(runners) + 2


def autosize_columns(ws) -> None:
    fixed_widths = {
        "A": 34,
        "B": 12,
        "C": 13,
        "D": 10,
        "E": 3,
        "F": 34,
        "G": 12,
        "H": 13,
        "I": 10,
    }
    for col, width in fixed_widths.items():
        ws.column_dimensions[col].width = width


def build_workbook(parsed: ParsedRaceFile) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Daily Output"
    ws.sheet_view.showGridLines = False

    ws.merge_cells("A1:I1")
    ws["A1"] = "Race Figure Output"
    ws["A1"].fill = PatternFill("solid", fgColor=TITLE_FILL)
    ws["A1"].font = Font(bold=True, color=WHITE, size=14)
    ws["A1"].alignment = Alignment(vertical="center")

    ws.merge_cells("A2:I2")
    ws["A2"] = "Sorted by Weight lbs - Last Speed Figure, lowest first."
    ws["A2"].fill = PatternFill("solid", fgColor="F2F6F7")
    ws["A2"].font = Font(color=TITLE_FILL)

    row = 4
    col = 1
    left_height = 0

    for race in parsed.races:
        height = write_race_table(ws, race, row, col)
        if col == 1:
            left_height = height
            col = 6
        else:
            row += max(left_height, height) + 3
            col = 1
            left_height = 0

    if col == 6:
        row += left_height + 3

    autosize_columns(ws)
    ws.freeze_panes = "A3"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_margins = PageMargins(left=0.25, right=0.25, top=0.4, bottom=0.4)

    output = BytesIO()
    wb.save(output)
    return output.getvalue()


def output_filename(source_name: str) -> str:
    stem = Path(source_name).stem or "race-output"
    safe = "".join(char if char.isalnum() or char in (" ", "-", "_") else "-" for char in stem)
    return f"{safe.strip()} - Race Figures.xlsx"
