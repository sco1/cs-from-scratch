import datetime as dt
import typing as t
from array import array
from pathlib import Path

from PIL import Image

MAX_WIDTH = 576
MAX_HEIGHT = 720

MAC_BINARY_LENGTH = 128
HEADER_LENGTH = 512


def prepare_img(
    filepath: Path, max_width: int = MAX_WIDTH, max_height: int = MAX_HEIGHT
) -> Image.Image:
    """
    Load the specified image & resize if necessary.

    `max_width` and `max_height` may be specified to control the image size threshold, this function
    defaults to a maximum image size of `576`x`720` pixels to align with MacPaint's maximum
    dimensions.
    """
    with filepath.open("rb") as f:
        img = Image.open(f)

        if (img.width > max_width) or (img.height > max_height):
            final_aspect_ratio = max_width / max_height
            current_ratio = img.width / img.height
            if current_ratio >= final_aspect_ratio:
                new_size = (max_width, int(img.height * (max_width / img.width)))
            else:
                new_size = (int(img.width * (max_height / img.height)), max_height)

            img.thumbnail(new_size, Image.Resampling.LANCZOS)

        # Convert to grayscale
        return img.convert("L")


def bytes_to_bits(data: array) -> array:
    """
    Convert the provided byte array into a bit array.

    It is assumed that the array of bytes contains bytes that are either `0` or `255`. This array
    is converted into an array of bits, where `0` becomes `1` (black) and `255` becomes `0` (white),
    to align with MacPaint's bitmap format.
    """
    bits_array = array("B")

    for byte_idx in range(0, len(data), 8):
        next_byte = 0
        for bit_idx in range(8):
            # Note that since we only have 255 or 0, we only need to check the first bit
            next_bit = 1 - (data[byte_idx + bit_idx] & 1)  # Invert the black/white pixel value
            next_byte = next_byte | (next_bit << (7 - bit_idx))
            if (byte_idx + bit_idx + 1) >= len(data):
                break

        bits_array.append(next_byte)

    return bits_array


def prepare_array(data: array, width: int, height: int) -> array:
    """
    Convert the provided image byte array into a MacPaint compatible bit array.

    As MacPaint only utilizes white (`0`) and black (`1`) pixels and we assume that the provided
    image byte array only contains white (`255`) and black (`0`) pixels, the image byte array can be
    converted into a bit array for output. MacPaint bitmaps need to be padded with white pixels
    where the incoming pixel data does not extend to the full size of the image.
    """
    bits_array = array("B")
    for y in range(height):
        img_location = y * width
        img_bits = bytes_to_bits(data[img_location : (img_location + width)])
        bits_array += img_bits

        remaining_width = MAX_WIDTH - width
        width_padding = array("B", [0] * (remaining_width // 8))
        bits_array += width_padding

    remaining_height = MAX_HEIGHT - height
    height_padding = array("B", [0] * ((remaining_height * MAX_WIDTH) // 8))
    bits_array += height_padding

    return bits_array


def unsigned_packbits(source_data: array) -> array:
    """
    An unsigned integer implementation of the Apple PackBits run-length encoding scheme.

    Where the original PackBits scheme utilized signed integers, this implementation adjusts the
    encoding scheme to function with unsigned integers.

    The value of `n` is adjusted as follows:
        * `0` to `127` - `n+1` literal bytes follow
        * `129` to `255` - The next byte is repeated `257-n` times
        * `128` - Skip

    Single values are encoded as literals, e.g. `[0x00]` would be encoded as `[0x00, 0x00]`.

    NOTE: The MacPaint file format specifies that each row is individually run-length encoded.
    """

    def take_same(src: array, start: int) -> int:
        """Count how many of the same bytes follow the starting byte within the same row."""
        count = 0
        while (start + count + 1 < len(src)) and (src[start + count] == src[start + count + 1]):
            count += 1

        if count > 0:
            return count + 1
        else:
            return 0

    rle_data = array("B")
    for line_start in range(0, len(source_data), MAX_WIDTH // 8):  # per-row RLE
        data = source_data[line_start : (line_start + (MAX_WIDTH // 8))]

        idx = 0
        while idx < len(data):
            not_same = 0
            while ((same := take_same(data, idx + not_same)) == 0) and (idx + not_same < len(data)):
                # literal run
                not_same += 1

            # We get here once a literal run isn't found, this can happen one of three ways:
            #     1. A repeat run is immediately found
            #     2. A literal run is initially found, then a repeat run is found
            #     3. A literal run is found that spans the entire row
            #
            # Because of #2, there may be a case where `same` and `not_same` are both > 0, and both
            # would need to be encoded
            if not_same > 0:  # literal run
                rle_data.append(not_same - 1)
                rle_data += data[idx : (idx + not_same)]
                idx += not_same

            if same > 0:  # repeat run
                rle_data.append(257 - same)
                rle_data.append(data[idx])
                idx += same

    return rle_data


def _str2array(in_str: str, fmt: str = "mac_roman") -> array:
    return array("B", in_str.encode(fmt))


def _int2array(
    in_data: int, n_bytes: int = 4, byteorder: t.Literal["little", "big"] = "big"
) -> array:
    return array("B", in_data.to_bytes(n_bytes, byteorder=byteorder))


def prepare_macbinary_header(out_filepath: Path, data_size: int) -> array:
    """
    Prepare the required header MacBinary header fields for a MacPaint file.

    The required fields are as follows:

    | Offset | Length      | Type     | Value                                      |
    |--------|-------------|----------|--------------------------------------------|
    | `1`    | `1`         | Integer  | Filename length (up to `63`)               |
    | `2`    | `1` to `63` | MacRoman | Filename                                   |
    | `65`   | `4`         | MacRoman | File type (`"PNTG"`)                       |
    | `69`   | `4`         | MacRoman | File creator (`"MPNT"`)                    |
    | `83`   | `4`         | Integer  | Data fork length                           |
    | `91`   | `4`         | Integer  | Creation time, seconds from `1/1/1904`     |
    | `95`   | `4`         | Integer  | Modification time, seconds from `1/1/1904` |

    NOTE: Filenames greater than `63` characters are truncated.

    NOTE: Integer values are stored big-endian.
    """
    macbinary = array("B", [0] * MAC_BINARY_LENGTH)

    filename = out_filepath.stem
    if len(filename) > 63:  # Truncate filename if necessary
        filename = filename[:63]

    macbinary[1] = len(filename)
    macbinary[2 : (2 + len(filename))] = _str2array(filename)
    macbinary[65:69] = _str2array("PNTG")  # File type
    macbinary[69:73] = _str2array("MPNT")  # File creator
    macbinary[83:87] = _int2array(data_size)  # Size of data fork

    timestamp = int((dt.datetime.now() - dt.datetime(1904, 1, 1)).total_seconds())
    macbinary[91:95] = _int2array(timestamp)  # Creation timestamp
    macbinary[95:99] = _int2array(timestamp)  # Modification timestamp

    return macbinary


def write_macpaint(data: array, out_filepath: Path, width: int, height: int) -> None:
    """Write the provided image byte array to a MacPaint file."""
    bits_array = prepare_array(data, width=width, height=height)
    packed = unsigned_packbits(bits_array)
    data_size = len(packed) + HEADER_LENGTH

    header = prepare_macbinary_header(out_filepath, data_size)
    out_data = header + array("B", [0] * HEADER_LENGTH) + packed
    out_data[MAC_BINARY_LENGTH + 3] = 2

    padding = 128 - (data_size % 128)
    if padding > 0:
        out_data += array("B", [0] * padding)

    out_filepath.write_bytes(out_data)
