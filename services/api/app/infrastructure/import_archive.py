"""Verify that a strict learning ZIP accounts for every original input byte.

Prefixed/concatenated archives, trailing data, arbitrary extra fields/comments,
and unclaimed gaps are not a complete learning-package envelope. This does not
extract payloads or replace the parser's manifest/hash/visibility validation.
"""

from io import BytesIO
import struct
from zipfile import BadZipFile, ZipFile


def has_complete_archive_envelope(data: bytes) -> bool:
    try:
        with ZipFile(BytesIO(data)) as archive:
            entries = archive.infolist()
            if archive.comment:
                return False
            position = 0
            for entry in sorted(entries, key=lambda item: item.header_offset):
                if (entry.header_offset != position or entry.extra or entry.comment or entry.flag_bits & 8
                        or data[position:position + 4] != b"PK\x03\x04"):
                    return False
                name_length, extra_length = struct.unpack_from("<HH", data, position + 26)
                if extra_length:
                    return False
                position += 30 + name_length + entry.compress_size
            central_start = position
            for _ in entries:
                if data[position:position + 4] != b"PK\x01\x02":
                    return False
                name_length, extra_length, comment_length = struct.unpack_from("<HHH", data, position + 28)
                if extra_length or comment_length:
                    return False
                position += 46 + name_length
            if len(data) != position + 22:
                return False
            signature, disk, central_disk, disk_count, count, size, offset, comment_size = struct.unpack_from("<4s4H2LH", data, position)
            return (signature == b"PK\x05\x06" and disk == central_disk == comment_size == 0
                    and disk_count == count == len(entries) and offset == central_start and size == position - central_start)
    except (BadZipFile, ValueError, TypeError, struct.error, OverflowError):
        return False
