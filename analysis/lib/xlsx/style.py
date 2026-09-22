from math import ceil

from openpyxl.styles import (
    Alignment,
    Border,
    Font,
    NamedStyle,
    PatternFill,
    Side,
)
from openpyxl.utils.cell import get_column_letter

# Guess at how many characters fit into a column width measurement
CHAR_PER_WIDTH_UNIT = 1.2

### Create named styles for formatting cells
font_bold = Font(bold=True)

alignment_left_wrap = Alignment(horizontal="left", wrap_text=True)
alignment_center_wrap = Alignment(horizontal="center", wrap_text=True)

default_header_border = Border(
    bottom=Side(border_style="medium", color="000000"),
)
default_cell_border = Border(
    bottom=Side(border_style="thin", color="AAAAAA"),
    left=Side(border_style="thin", color="DDDDDD"),
    right=Side(border_style="thin", color="DDDDDD"),
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

good_condition_header_style = NamedStyle(
    name="Good Condition Header Style",
    alignment=alignment_center_wrap,
    border=Border(
        bottom=Side(border_style="thin", color="000000"),
    ),
    fill=PatternFill("solid", "EEEEEE"),
)


value_style = NamedStyle(
    name="Value Style",
    alignment=alignment_left_wrap,
    border=default_cell_border,
)

even_row_bg = PatternFill("solid", fgColor="00F6F6F6")

analysis_unit_divider = Border(
    bottom=Side(border_style="medium", color="AAAAAA"),
    left=Side(border_style="thin", color="DDDDDD"),
    right=Side(border_style="thin", color="DDDDDD"),
)

description_font = Font(color="999999")


def set_cell_styles(ws, breaks=None, area_columns=None, percent_columns=None, add_percent_divider=False):
    area_columns = area_columns or []
    percent_columns = percent_columns or []

    for col_idx, col in enumerate(ws.columns):
        col[0].style = center_header_style

        for i, cell in enumerate(col[1:]):
            cell.style = value_style
            value = cell.value
            is_int = isinstance(value, (float, int)) and int(value) == value

            if col_idx in area_columns:
                if is_int:
                    cell.number_format = "#,##0"
                else:
                    cell.number_format = "#,##0.00"
            elif col_idx in percent_columns:
                if is_int:
                    cell.number_format = "0%"
                else:
                    cell.number_format = "0.00%"

            if i % 2 == 1:
                cell.fill = even_row_bg

    ws["A1"].style = left_header_style

    if breaks is not None:
        # add a stronger line between analysis units
        for col in ws.columns:
            for line in breaks:
                col[line].border = analysis_unit_divider

    if add_percent_divider and len(percent_columns) > 0:
        # add a line between areas and percents
        percent_start_col = get_column_letter(percent_columns[0] + 1)
        for i in range(1, ws.max_row + 1):
            cell = ws[f"{percent_start_col}{i}"]
            cell.border = Border(
                left=Side(border_style="medium", color="666666"), bottom=cell.border.bottom, right=cell.border.right
            )


def set_column_widths(ws, widths):
    for i, width in enumerate(widths):
        letter = get_column_letter(i + 1)
        ws.column_dimensions[letter].width = width


def add_caption(ws, table_counter, caption):
    """Add a table caption followed by a blank line

    Parameters
    ----------
    ws : Worksheet
    table_counter : int
    caption : str
    """

    ws.insert_rows(idx=1, amount=2)

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
