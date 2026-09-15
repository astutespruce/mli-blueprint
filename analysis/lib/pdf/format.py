def format_number(number):
    """Format numbers for display.

    if < 1, return 2 decimal places
    if <10, return 1 decimal places
    otherwise, return comma formatted number with no decimal places

    Parameters
    ----------
    number : float

    Returns
    -------
    string
    """
    if number == 0:
        return "0"

    if number < 0.01:
        return "< 0.01"

    if number < 1:
        round1 = int(round(number * 10)) / 10
        if round1 == number:
            return f"{round1:.1f}"
        else:
            number = int(round(number * 100)) / 100
            return f"{number:.2f}"

    if number < 10:
        if int(number) == number:
            return f"{number:.0f}"

        number = int(round(number * 10)) / 10
        if int(number) == number:
            return f"{number:.0f}"

        return f"{number:.1f}"

    return f"{number:,.0f}"


def format_percent(number):
    """Format percents for display.
    uses 1 decimal place (if needed), clipped to [0, 100] range.
    """

    if number == 0:
        return "0"

    if number == 100:
        return "100"

    if number < 0.1:
        return "<0.1"

    return f"{min(round(number, 1), 100):.1f}"
