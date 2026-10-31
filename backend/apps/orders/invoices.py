from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def render_invoice(order):
    font_path = Path(reportlab.__file__).parent / "fonts" / "Vera.ttf"
    if "InvoiceSans" not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(TTFont("InvoiceSans", str(font_path)))
    output = BytesIO()
    document = SimpleDocTemplate(
        output,
        pagesize=(210 * mm, 297 * mm),
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=f"Invoice {order.number}",
        author=order.invoice_snapshot.get("name", ""),
    )
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("Body", fontName="InvoiceSans", fontSize=9, leading=14, spaceAfter=4))
    styles.add(ParagraphStyle("Amount", parent=styles["Body"], alignment=TA_RIGHT))

    def text(value, style="Body"):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    seller = order.invoice_snapshot
    story = [
        Paragraph("INVOICE", styles["Title"]),
        Spacer(1, 8 * mm),
        text(seller.get("name", "")),
        text(seller.get("address", "")),
        text(seller.get("email", "")),
        text(f"Tax registration: {seller.get('tax_number') or 'Not provided'}"),
        Spacer(1, 5 * mm),
        text(f"Invoice: INV-{order.number[3:]}"),
        text(f"Issued: {order.confirmed_at:%Y-%m-%d} | Order: {order.number}"),
        text(f"Currency: {order.currency} | Payment: {order.payment_status}"),
        Spacer(1, 5 * mm),
        text("BILL TO"),
        text(order.customer_name),
        text(order.customer_address),
        text(order.customer_email),
        Spacer(1, 6 * mm),
    ]
    rows = [[text(v) for v in ["Product / SKU", "Qty", "Unit price", "Amount"]]]
    for item in order.items.all():
        rows.append(
            [
                text(f"{item.product_name}\n{item.sku}"),
                text(item.quantity, "Amount"),
                text(f"{item.unit_price:,.2f}", "Amount"),
                text(f"{item.line_total:,.2f}", "Amount"),
            ]
        )
    table = LongTable(rows, colWidths=[88 * mm, 15 * mm, 32 * mm, 35 * mm], repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8f0ef")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#ccd5de")),
            ]
        )
    )
    story += [table, Spacer(1, 6 * mm)]
    totals = Table(
        [
            [text("Subtotal"), text(f"{order.subtotal:,.2f}", "Amount")],
            [text(f"Tax ({order.tax_rate}%)"), text(f"{order.tax_amount:,.2f}", "Amount")],
            [text(f"TOTAL ({order.currency})"), text(f"{order.total:,.2f}", "Amount")],
        ],
        colWidths=[130 * mm, 40 * mm],
    )
    story += [totals, Spacer(1, 8 * mm), text(order.notes)]

    def footer(canvas, doc):
        canvas.setFont("InvoiceSans", 8)
        canvas.setFillColor(colors.HexColor("#657085"))
        canvas.drawString(20 * mm, 12 * mm, f"INV-{order.number[3:]} | {order.currency}")
        canvas.drawRightString(190 * mm, 12 * mm, f"Page {doc.page}")

    document.build(story, onFirstPage=footer, onLaterPages=footer)
    output.seek(0)
    return output
