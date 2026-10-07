from math import ceil

from openpyxl.styles import Alignment, Border, Font, NamedStyle, PatternFill, Side
from openpyxl.utils.cell import get_column_letter

# Guess at how many characters fit into a column width measurement
CHAR_PER_WIDTH_UNIT = 1.2

### Create named styles for formatting cells
font_bold = Font(bold=True)

alignment_left_wrap = Alignment(horizontal="left", wrap_text=True)
alignment_center_wrap = Alignment(horizontal="center", wrap_text=True)

default_header_border = Border(
    top=Side(border_style="medium", color="000000"),
    bottom=Side(border_style="medium", color="000000"),
)

# Note: all cells are setup to wrap text
left_header_style = NamedStyle(
    name="Left Header Style",
    font=font_bold,
    alignment=alignment_left_wrap,
    border=default_header_border,
)

center_header_style = NamedStyle(
    name="Center Header Style",
    font=font_bold,
    alignment=alignment_center_wrap,
    border=default_header_border,
)

table_caption_style = NamedStyle(
    name="Table Header Style",
    font=Font(italic=True),
    alignment=Alignment(vertical="top", horizontal="left", wrap_text=True),
)

acres_percent_header_style = NamedStyle(
    name="Acres and Percent Header Style",
    alignment=Alignment(horizontal="center", vertical="center", wrap_text=True),
    font=Font(bold=True),
    border=Border(
        top=Side(border_style="medium", color="000000"),
        left=Side(border_style="thin", color="000000"),
        bottom=Side(border_style="medium", color="000000"),
        right=Side(border_style="thin", color="000000"),
    ),
    fill=PatternFill("solid", "eceeef"),
)


good_condition_header_style = NamedStyle(
    name="Good Condition Header Style",
    alignment=Alignment(horizontal="center", vertical="center", wrap_text=True),
    font=Font(italic=True, color="FFFFFF", bold=True),
    border=Border(
        top=Side(border_style="medium", color="000000"),
        bottom=Side(border_style="thin", color="000000"),
    ),
    fill=PatternFill("solid", "333333"),
)

not_good_condition_header_style = NamedStyle(
    name="Not Good Condition Header Style",
    alignment=Alignment(horizontal="center", vertical="center", wrap_text=True),
    font=Font(italic=True, color="333333"),
    border=Border(
        top=Side(border_style="medium", color="000000"),
        bottom=Side(border_style="thin", color="000000"),
    ),
    fill=PatternFill("solid", "f9f9fa"),
)

value_style = NamedStyle(name="Value Style", alignment=alignment_left_wrap, border=None)

divider_col_style = NamedStyle(
    name="Divider Column Style",
    border=Border(
        left=Side(border_style="thin", color="000000"),
        right=Side(border_style="thin", color="000000"),
    ),
)


def add_caption(ws, table_counter, caption):
    """Add a table caption in the first cell of the table, and merge all cells
    of that row together.

    Parameters
    ----------
    ws : Worksheet
    table_counter : int
    caption : str
    """

    cell = ws["A1"]
    cell.value = f"Table {table_counter}: {caption}"
    cell.style = table_caption_style

    end_col = get_column_letter(ws.max_column)
    ws.merge_cells(f"A1:{end_col}1")

    # Excel does not auto-calculate the height properly for merged cells with wrapping
    # so we calculate the height based on the approx number of lines of text for the width
    width = sum(ws.column_dimensions[get_column_letter(i)].width for i in range(1, ws.max_column + 1))
    chars_per_line = width * CHAR_PER_WIDTH_UNIT
    total_line_height = sum([max(1, ceil(len(line) / chars_per_line)) * 16 for line in caption.split("\n")])
    # default is height 20, but extend up to 16 units per line of text
    ws.row_dimensions[1].height = max(20, total_line_height)


def add_acres_percent_header(ws, row_idx: int, area_columns: list[int], percent_columns: list[int]):
    """Add a header row for the acres and percent sections

    Parameters
    ----------
    ws : Worksheet
    row_idx : int
        1-based row index where header will be set
    area_columns : list[int] | None, optional
        0-based indexes of area columns within the columns of the dataframe.
    percent_columns : list[int] | None, optional
        0-based indexes of percent value columns within the columns of the dataframe.
    """
    ws.row_dimensions[row_idx].height = 32

    start_cell = f"{get_column_letter(area_columns[0] + 1)}{row_idx}"
    cell = ws[start_cell]
    cell.value = "ACRES"
    cell.style = acres_percent_header_style
    ws.merge_cells(f"{start_cell}:{get_column_letter(area_columns[-1] + 1)}{row_idx}")

    start_cell = f"{get_column_letter(percent_columns[0] + 1)}{row_idx}"
    cell = ws[start_cell]
    cell.value = "PERCENT"
    cell.style = acres_percent_header_style
    ws.merge_cells(f"{start_cell}:{get_column_letter(percent_columns[-1])}{row_idx}")

    # set gap column between acres and percents
    ws[f"{get_column_letter(percent_columns[0])}{row_idx}"].style = divider_col_style

    # set borders for preceding columns
    for col_idx in range(1, area_columns[0] + 1):
        cell = ws[f"{get_column_letter(col_idx)}{row_idx}"]
        cell.border = default_header_border
