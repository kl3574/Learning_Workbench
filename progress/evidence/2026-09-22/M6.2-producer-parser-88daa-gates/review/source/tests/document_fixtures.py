"""Original deterministic document bytes; all text and drawings are synthetic."""

from io import BytesIO
import struct
import zlib
from zipfile import ZipFile, ZipInfo, ZIP_STORED


def formula_pixels() -> tuple[int, int, bytes]:
    """Original bitmap x²: no formula exists in the PDF text layer."""
    width, height, scale = 72, 48, 4
    pixels = bytearray(b"\xff" * width * height * 3)
    glyphs = [(2, 4, ["10001", "01010", "00100", "01010", "10001"]),
              (8, 1, ["111", "001", "111", "100", "111"])]
    for left, top, rows in glyphs:
        for row, bits in enumerate(rows):
            for col, bit in enumerate(bits):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            position = (((top + row) * scale + dy) * width + (left + col) * scale + dx) * 3
                            pixels[position:position + 3] = b"\x00\x00\x00"
    return width, height, bytes(pixels)


def formula_png() -> bytes:
    width, height, pixels = formula_pixels()
    def chunk(kind: bytes, value: bytes) -> bytes:
        return struct.pack(">I", len(value)) + kind + value + struct.pack(">I", zlib.crc32(kind + value))
    rows = b"".join(b"\x00" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b"")


def _pdf(pages: list[bytes], *, image: bool = True) -> bytes:
    objects: list[bytes] = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    if image:
        width, height, pixels = formula_pixels()
        objects.append(f"<< /Type /XObject /Subtype /Image /Width {width} /Height {height} /ColorSpace /DeviceRGB /BitsPerComponent 8 /Length {len(pixels)} >>\nstream\n".encode() + pixels + b"\nendstream")
    kids = []
    for content in pages:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        resources = "/Font << /F1 3 0 R >>" + (" /XObject << /Im1 4 0 R >>" if image else "")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << {resources} >> /Contents {page_id + 1} 0 R >>".encode())
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(pages)} /Kids [{' '.join(kids)}] >>".encode()
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, value in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + value + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(data)


def pdf_text_fixture() -> bytes:
    return _pdf([
        b"BT /F1 12 Tf 50 740 Td (PDF page one alpha.) Tj ET\nBT /F1 12 Tf 50 650 Td (Left column line one) Tj 0 -20 Td (Left column line two) Tj ET\nBT /F1 12 Tf 330 650 Td (Right column line one) Tj 0 -20 Td (Right column line two) Tj ET\n",
        b"BT /F1 12 Tf 50 740 Td (PDF page two beta.) Tj ET\n50 580 300 60 re S\n200 580 m 200 640 l S\nBT /F1 12 Tf 70 610 Td (Cell A) Tj 170 0 Td (Cell B) Tj ET\nq 144 0 0 96 50 450 cm /Im1 Do Q\n",
    ])


def pdf_scan_fixture() -> bytes:
    return _pdf([b"q 500 0 0 700 50 50 cm /Im1 Do Q\n"])


def pdf_mixed_fixture() -> bytes:
    return _pdf([b"BT /F1 12 Tf 50 740 Td (Readable first page.) Tj ET\n", b"q 500 0 0 700 50 50 cm /Im1 Do Q\n"])


def pdf_encrypted_fixture() -> bytes:
    from pypdf import PdfReader, PdfWriter
    writer = PdfWriter(clone_from=PdfReader(BytesIO(pdf_text_fixture())))
    writer.encrypt("synthetic-password", algorithm="RC4-128")
    stream = BytesIO()
    writer.write(stream)
    return stream.getvalue()


def pdf_malformed_fixture() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<< broken synthetic PDF\n"


DOCX_DOCUMENT = '''<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
<w:body>
<w:p><w:pPr><w:pStyle w:val="Heading1"/></w:pPr><w:r><w:t>Synthetic DOCX</w:t></w:r></w:p>
<w:p><w:r><w:t>DOCX paragraph alpha</w:t></w:r></w:p>
<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Cell B</w:t></w:r></w:p></w:tc></w:tr></w:tbl>
<w:p><m:oMath><m:f><m:num><m:r><m:t>x</m:t></m:r></m:num><m:den><m:r><m:t>2</m:t></m:r></m:den></m:f></m:oMath></w:p>
<w:p><w:r><w:drawing><wp:anchor><a:graphic><a:graphicData><a:blip r:embed="rImage"/></a:graphicData></a:graphic></wp:anchor></w:drawing></w:r></w:p>
<w:p><w:hyperlink r:id="rLink"><w:r><w:t>External reference</w:t></w:r></w:hyperlink><w:r><w:drawing><wp:inline><a:graphic><a:graphicData><a:blip r:link="rRemoteImage"/></a:graphicData></a:graphic></wp:inline></w:drawing></w:r></w:p>
<w:sectPr/>
</w:body></w:document>'''


def docx_payloads() -> dict[str, bytes]:
    prefix = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/"
    return {
        "[Content_Types].xml": b'<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/><Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>',
        "_rels/.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rDocument" Type="{prefix}officeDocument" Target="word/document.xml"/></Relationships>'.encode(),
        "word/document.xml": DOCX_DOCUMENT.encode(),
        "word/_rels/document.xml.rels": f'<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rImage" Type="{prefix}image" Target="media/synthetic.png"/><Relationship Id="rLink" Type="{prefix}hyperlink" Target="https://example.invalid/reference" TargetMode="External"/><Relationship Id="rRemoteImage" Type="{prefix}image" Target="https://example.invalid/private-image" TargetMode="External"/></Relationships>'.encode(),
        "word/media/synthetic.png": formula_png(),
    }


def docx_from_payloads(payloads: dict[str, bytes]) -> bytes:
    stream = BytesIO()
    with ZipFile(stream, "w", compression=ZIP_STORED) as archive:
        for path, value in payloads.items():
            archive.writestr(ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0)), value)
    return stream.getvalue()


def docx_fixture() -> bytes:
    return docx_from_payloads(docx_payloads())


def docx_malformed_fixture() -> bytes:
    payloads = docx_payloads()
    payloads["word/document.xml"] = b"<broken>"
    return docx_from_payloads(payloads)


def docx_dtd_fixture() -> bytes:
    payloads = docx_payloads()
    payloads["word/document.xml"] = b'<!DOCTYPE doc [<!ENTITY external SYSTEM "file:///synthetic-private">]><doc>&external;</doc>'
    return docx_from_payloads(payloads)
