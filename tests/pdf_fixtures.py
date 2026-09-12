"""Small real PDF fixtures for parser tests."""
import io

def pdf_bytes(page_texts, image_only=False):
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"", b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    kids = []
    for text in page_texts:
        page_id = len(objects) + 1
        kids.append(f"{page_id} 0 R")
        if image_only:
            commands = b"q 100 0 0 100 40 500 cm BI /W 1 /H 1 /CS /RGB /BPC 8 ID " + bytes([100,100,100]) + b" EI Q"
        else:
            commands = b"BT /F1 12 Tf 40 750 Td 15 TL "
            for line in text.splitlines():
                escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
                commands += b"(" + escaped.encode("ascii") + b") Tj T* "
            commands += b"ET"
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 3 0 R >> >> /Contents {page_id+1} 0 R >>".encode())
        objects.append(f"<< /Length {len(commands)} >>\nstream\n".encode() + commands + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(kids)}] >>".encode()
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(output)
    output.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return bytes(output)

def upload(texts, image_only=False):
    result = io.BytesIO(pdf_bytes(texts, image_only))
    result.name = "sample.pdf"
    result.size = len(result.getvalue())
    return result
