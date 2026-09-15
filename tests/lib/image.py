from io import BytesIO
from pathlib import Path

from PIL import Image
from pixelmatch.contrib.PIL import pixelmatch


def image_matches(img_data, expected_filename, tolerance=0):
    """Compare image bytes to expected image file

    Parameters
    ----------
    img_data : bytes
    expected_filename : str
    tolerance : int
        number of pixels that are allowed to be different

    Returns
    -------
    True if images match exactly, False otherwise
    """
    buffer = BytesIO(img_data)
    actual = Image.open(buffer)
    expected = Image.open(expected_filename)

    actual.save(f"/tmp/{Path(expected_filename).name}")

    if actual.size != expected.size:
        return False

    diff = pixelmatch(actual, expected, includeAA=False, threshold=0.1285)
    matches = diff <= tolerance

    if not matches:
        print(f"{expected_filename} differs by {diff} pixels")

    return matches
