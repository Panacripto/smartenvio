import base64, os
from io import BytesIO
from fpdf import FPDF

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
SELLO_PATH = os.path.join(ROOT, "SELLO PROCESADO.png")

ARIAL = r"C:\Windows\Fonts\arial.ttf"
ARIAL_B = r"C:\Windows\Fonts\arialbd.ttf"
ARIAL_I = r"C:\Windows\Fonts\ariali.ttf"


def _fmt(n: float) -> str:
    return f"{n:,.2f}"


def _precio_bs(line: dict) -> float:
    pcio = float(line.get("FDI_PRECIODEVENTA") or 0)
    moneda = int(line.get("FDI_MONEDA") or 0)
    factor = float(line.get("FDI_FACTORCAMBIO") or 1)
    if factor == 0:
        factor = 1
    if moneda == 1:
        return pcio / factor
    else:
        return pcio * factor


def _sanitize(s: str) -> str:
    return s.replace("\r", " ").replace("\n", " ")


def generar_factura_pdf(
    invoice: dict,
    detail_lines: list[dict],
    client_data: dict | None = None,
    company: dict | None = None,
) -> str:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("Arial", "", ARIAL)
    pdf.add_font("Arial", "B", ARIAL_B)
    pdf.add_font("Arial", "I", ARIAL_I)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    pw = pdf.w - 2 * pdf.l_margin

    # ── Sello "PROCESADO" (marca de agua) ──
    if company and company.get("incluir_sello", True):
        if os.path.exists(SELLO_PATH):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(SELLO_PATH).convert("RGBA")
                r, g, b, a = img.split()
                a = a.point(lambda x: int(x * 0.12))
                img = PILImage.merge("RGBA", (r, g, b, a))
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                with pdf.rotation(35, x=pdf.w / 2, y=pdf.h / 2):
                    pdf.image(buf, x=pdf.l_margin + 15, y=pdf.t_margin + 60, w=150)
            except:
                pass

    # ── Logo (izquierda) ──
    if company:
        logo_b64 = company.get("empresa_logo", "")
        if logo_b64:
            try:
                from PIL import Image as PILImage
                logo_data = base64.b64decode(logo_b64)
                logo_img = PILImage.open(BytesIO(logo_data))
                iw, ih = logo_img.size
                logo_max = 22
                if iw / ih > 1:
                    logo_w = logo_max
                    logo_h = logo_max * ih / iw
                else:
                    logo_h = logo_max
                    logo_w = logo_max * iw / ih
                pdf.image(BytesIO(logo_data), x=pdf.l_margin, y=pdf.t_margin, w=logo_w, h=logo_h)
                pdf.set_y(pdf.t_margin + logo_max + 2)
            except:
                pass

    # ── Title ──
    pdf.set_font("Arial", "B", 22)
    pdf.cell(pw, 12, "SOPORTE DE TRANSACCION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    # ── Invoice info ──
    pdf.set_font("Arial", "B", 10)
    doc = _sanitize(str(invoice.get("FTI_DOCUMENTO", "")))
    pdf.cell(pw, 6, f"Numero: {doc}", new_x="LMARGIN", new_y="NEXT")
    fecha = _sanitize(str(invoice.get("FTI_FECHAEMISION", ""))[:10])
    pdf.cell(pw, 6, f"Fecha: {fecha}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # ── Company info ──
    if company:
        pdf.set_font("Arial", "B", 11)
        pdf.set_fill_color(240, 240, 240)
        pdf.cell(pw, 7, "EMISOR", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)
        pdf.set_font("Arial", "", 9)
        razon = _sanitize(str(company.get("empresa_razon_social") or ""))
        if razon:
            pdf.cell(pw, 5, f"Razon Social: {razon}", new_x="LMARGIN", new_y="NEXT")
        rif = _sanitize(str(company.get("empresa_rif") or ""))
        if rif:
            pdf.cell(pw, 5, f"RIF: {rif}", new_x="LMARGIN", new_y="NEXT")
        dir_emp = _sanitize(str(company.get("empresa_direccion") or ""))
        if dir_emp:
            pdf.cell(pw, 5, f"Direccion: {dir_emp}", new_x="LMARGIN", new_y="NEXT")
        tel_emp = _sanitize(str(company.get("empresa_telefono") or ""))
        if tel_emp:
            pdf.cell(pw, 5, f"Telefono: {tel_emp}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # ── Separator ──
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.ln(4)

    # ── Client data ──
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(pw, 7, "DATOS DEL CLIENTE", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("Arial", "", 9)
    cliente = _sanitize(str(invoice.get("FTI_PERSONACONTACTO") or (client_data.get("FC_DESCRIPCION") if client_data else "") or ""))
    pdf.cell(pw, 5, f"Cliente: {cliente}", new_x="LMARGIN", new_y="NEXT")
    rif = _sanitize(str(invoice.get("FTI_RIFCLIENTE") or ""))
    if rif:
        pdf.cell(pw, 5, f"RIF: {rif}", new_x="LMARGIN", new_y="NEXT")
    dirs = []
    for k in ("FC_DIRECCION1", "FC_DIRECCION2", "FC_DIRECCION3"):
        v = _sanitize(str(client_data.get(k) or ""))
        if v:
            dirs.append(v)
    if dirs:
        pdf.cell(pw, 5, f"Direccion: {', '.join(dirs)}", new_x="LMARGIN", new_y="NEXT")
    tel = _sanitize(str(invoice.get("FTI_TELEFONOCONTACTO") or ""))
    if tel:
        pdf.cell(pw, 5, f"Telefono: {tel}", new_x="LMARGIN", new_y="NEXT")

    pdf.ln(4)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.ln(4)

    # ── Detail table ──
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(pw, 7, "DETALLE DE LA FACTURA", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    col_w = [8, 16, 98, 20, 22, 26]
    headers = ["#", "Codigo", "Producto", "Cant.", "P.Unit BS", "Total"]

    pdf.set_font("Arial", "B", 7)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 6, h, border=1, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()

    pdf.set_font("Arial", "", 7.5)
    fill = False
    for i, line in enumerate(detail_lines, 1):
        cod = _sanitize(str(line.get("FDI_CODIGO") or ""))
        desc = _sanitize(str(line.get("producto_desc") or line.get("FDI_DESCRIPCIONOFERTA") or ""))
        und = str(line.get("FI_UNIDAD") or "")
        cant = float(line.get("FDI_CANTIDAD") or 0)
        pcio_bs = _precio_bs(line)
        total = cant * pcio_bs
        if fill:
            pdf.set_fill_color(245, 245, 245)
        else:
            pdf.set_fill_color(255, 255, 255)

        row_h = 6
        rows_needed = 1
        desc_w = col_w[2]
        if pdf.get_string_width(desc) > desc_w:
            rows_needed = max(rows_needed, int(pdf.get_string_width(desc) / desc_w) + 1)
        row_h = max(6, rows_needed * 4)

        if pdf.get_y() + row_h > pdf.h - 25:
            pdf.add_page()
            pdf.set_font("Arial", "B", 7)
            pdf.set_fill_color(50, 50, 50)
            pdf.set_text_color(255, 255, 255)
            for h, w in zip(headers, col_w):
                pdf.cell(w, 6, h, border=1, align="C", fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            pdf.set_font("Arial", "", 7.5)

        pdf.cell(col_w[0], row_h, str(i), border=1, align="C", fill=fill)
        pdf.cell(col_w[1], row_h, cod, border=1, align="C", fill=fill)
        x_desc = pdf.get_x()
        y_desc = pdf.get_y()
        pdf.cell(col_w[2], row_h, "", border=1, fill=fill)
        pdf.set_xy(x_desc, y_desc)
        pdf.multi_cell(col_w[2], 4, desc, border=0, align="L")
        pdf.set_xy(x_desc + col_w[2], y_desc)
        pdf.cell(col_w[3], row_h, _fmt(cant), border=1, align="R", fill=fill)
        pdf.cell(col_w[4], row_h, _fmt(pcio_bs), border=1, align="R", fill=fill)
        pdf.cell(col_w[5], row_h, _fmt(total), border=1, align="R", fill=fill)
        pdf.ln()
        fill = not fill

    # ── Totals ──
    pdf.ln(3)
    label_w = 60
    val_w = 40

    total_neto = float(invoice.get("FTI_TOTALNETO") or 0)
    moneda = int(invoice.get("FTI_MONEDA") or 0)
    factor = float(invoice.get("FTI_FACTORREFERENCIA") or 1)
    if factor == 0:
        factor = 1
    if moneda == 2:
        total_bs = total_neto * factor
    else:
        total_bs = total_neto

    pdf.set_font("Arial", "B", 11)
    pdf.cell(pw - label_w - val_w, 7, "", border=0)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(label_w, 7, "TOTAL:", border=1, align="R", fill=True)
    pdf.cell(val_w, 7, _fmt(total_bs), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "", 10)

    # ── Footer ──
    pdf.ln(10)
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.ln(3)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(pw, 6, "** SIN DERECHO A CREDITO FISCAL **", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)
    pdf.set_font("Arial", "I", 7)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(pw, 4, "Enviado desde SmartEnvios", align="C")

    # ── Output ──
    buf = BytesIO()
    pdf.output(buf)
    pdf_bytes = buf.getvalue()
    return base64.b64encode(pdf_bytes).decode("ascii")
