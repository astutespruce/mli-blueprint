import numpy as np


def hex_to_uint8(hex_code):
    """Convert 6-digit hex code to triple of uint8 values

    Parameters
    ----------
    hex_code : str

    Returns
    -------
    (red, green, blue)
    """

    if len(hex_code) != 7:
        raise ValueError("Hex code must be 6 digits")

    value = hex_code[1:]

    return tuple(int(value[i : i + 2], 16) for i in range(0, 6, 2))


def interpolate_colormap(colormap):
    """Interpolate colors from a colormap with stops

    Parameters
    ----------
    colormap : dict
        key / value pairs of data value to associated color

    Returns
    -------
    list of hex color codes for the range between the lowest key and highest key
    """

    # convert color hex codes to uint8 triples
    colormap = [
        (value, hex_to_uint8(color)) for value, color in sorted(colormap.items())
    ]

    colors = []

    # interpolate in RGB space
    start_value, start_color = colormap[0]
    for end_value, end_color in colormap[1:]:
        x = np.arange(start_value, end_value)
        xp = np.asarray([start_value, end_value])
        red = np.interp(x, xp, np.asarray([start_color[0], end_color[0]]))
        green = np.interp(x, xp, np.asarray([start_color[1], end_color[1]]))
        blue = np.interp(x, xp, np.asarray([start_color[2], end_color[2]]))

        range_colors = np.dstack([red, green, blue])[0].astype("uint8")
        colors.extend([f"#{r:02X}{g:02X}{b:02X}" for r, g, b in range_colors])

        start_value = end_value
        start_color = end_color

    # add last color
    r, g, b = colormap[-1][1]
    colors.append(f"#{r:02X}{g:02X}{b:02X}")

    return colors
