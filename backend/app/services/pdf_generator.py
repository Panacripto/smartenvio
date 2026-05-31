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
    formato: str = "carta",
) -> str:
    if formato == "ticket":
        return _generar_ticket(invoice, detail_lines, client_data, company)
    elif formato == "media_carta":
        return _generar_media_carta(invoice, detail_lines, client_data, company)
    return _generar_carta(invoice, detail_lines, client_data, company)


# ── CARTA (A4) ──
def _generar_carta(invoice, detail_lines, client_data, company) -> str:
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.add_font("Arial", "", ARIAL)
    pdf.add_font("Arial", "B", ARIAL_B)
    pdf.add_font("Arial", "I", ARIAL_I)
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pw = pdf.w - 2 * pdf.l_margin

    _carta_watermark(pdf, company)
    _carta_logo(pdf, company)
    _carta_header(pdf, invoice, pw)
    _carta_company(pdf, company, pw)
    _carta_separator(pdf, pw)
    _carta_client(pdf, invoice, client_data, pw)
    _carta_separator(pdf, pw)
    _carta_detail_table(pdf, detail_lines, pw)
    _carta_totals(pdf, invoice, pw)
    _carta_footer(pdf, pw)

    buf = BytesIO()
    pdf.output(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _carta_watermark(pdf, company):
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


def _carta_logo(pdf, company):
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


def _carta_header(pdf, invoice, pw):
    pdf.set_font("Arial", "B", 22)
    pdf.cell(pw, 12, "SOPORTE DE TRANSACCION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 10)
    doc = _sanitize(str(invoice.get("FTI_DOCUMENTO", "")))
    pdf.cell(pw, 6, f"Numero: {doc}", new_x="LMARGIN", new_y="NEXT")
    fecha = _sanitize(str(invoice.get("FTI_FECHAEMISION", ""))[:10])
    pdf.cell(pw, 6, f"Fecha: {fecha}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)


def _carta_company(pdf, company, pw):
    if not company:
        return
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


def _carta_separator(pdf, pw):
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.ln(4)


def _carta_client(pdf, invoice, client_data, pw):
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


def _carta_detail_table(pdf, detail_lines, pw):
    pdf.set_font("Arial", "B", 11)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(pw, 7, "DETALLE DE LA FACTURA", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    col_w = [8, 16, pw - 8 - 16 - 20 - 22 - 26, 20, 22, 26]
    headers = ["#", "Codigo", "Producto", "Cant.", "P.Unit BS", "Total"]

    _carta_table_header(pdf, headers, col_w)
    pdf.set_font("Arial", "", 7.5)
    _carta_body_rows(pdf, detail_lines, col_w)
    pdf.ln(3)


def _carta_table_header(pdf, headers, col_w):
    pdf.set_font("Arial", "B", 7)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 6, h, border=1, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()


def _carta_body_rows(pdf, lines, col_w):
    fill = False
    for i, line in enumerate(lines, 1):
        cod = _sanitize(str(line.get("FDI_CODIGO") or ""))
        desc = _sanitize(str(line.get("producto_desc") or line.get("FDI_DESCRIPCIONOFERTA") or ""))
        cant = float(line.get("FDI_CANTIDAD") or 0)
        pcio_bs = _precio_bs(line)
        total = cant * pcio_bs
        pdf.set_fill_color(255, 255, 255)
        if fill:
            pdf.set_fill_color(245, 245, 245)

        desc_w = col_w[2]
        rows_needed = max(1, int(pdf.get_string_width(desc) / max(desc_w, 1)) + 1)
        row_h = max(6, rows_needed * 4)

        if pdf.get_y() + row_h > pdf.h - 25:
            pdf.add_page()
            _carta_table_header(pdf, ["#", "Codigo", "Producto", "Cant.", "P.Unit BS", "Total"], col_w)
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


def _carta_totals(pdf, invoice, pw):
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


def _carta_footer(pdf, pw):
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


# ── MEDIA CARTA (A5) ──
def _generar_media_carta(invoice, detail_lines, client_data, company) -> str:
    pdf = FPDF(orientation="P", unit="mm", format="A5")
    pdf.add_font("Arial", "", ARIAL)
    pdf.add_font("Arial", "B", ARIAL_B)
    pdf.add_font("Arial", "I", ARIAL_I)
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()
    pw = pdf.w - 2 * pdf.l_margin

    _mc_watermark(pdf, company)
    _mc_logo(pdf, company)
    _mc_header(pdf, invoice, pw)
    _mc_company(pdf, company, pw)
    _mc_separator(pdf, pw)
    _mc_client(pdf, invoice, client_data, pw)
    _mc_separator(pdf, pw)
    _mc_detail_table(pdf, detail_lines, pw)
    _mc_totals(pdf, invoice, pw)
    _mc_footer(pdf, pw)

    buf = BytesIO()
    pdf.output(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _mc_watermark(pdf, company):
    if company and company.get("incluir_sello", True):
        if os.path.exists(SELLO_PATH):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(SELLO_PATH).convert("RGBA")
                r, g, b, a = img.split()
                a = a.point(lambda x: int(x * 0.10))
                img = PILImage.merge("RGBA", (r, g, b, a))
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                with pdf.rotation(35, x=pdf.w / 2, y=pdf.h / 2):
                    pdf.image(buf, x=pdf.l_margin + 5, y=pdf.t_margin + 30, w=100)
            except:
                pass


def _mc_logo(pdf, company):
    if company:
        logo_b64 = company.get("empresa_logo", "")
        if logo_b64:
            try:
                from PIL import Image as PILImage
                logo_data = base64.b64decode(logo_b64)
                logo_img = PILImage.open(BytesIO(logo_data))
                iw, ih = logo_img.size
                logo_max = 14
                if iw / ih > 1:
                    logo_w = logo_max
                    logo_h = logo_max * ih / iw
                else:
                    logo_h = logo_max
                    logo_w = logo_max * iw / ih
                pdf.image(BytesIO(logo_data), x=pdf.l_margin, y=pdf.t_margin, w=logo_w, h=logo_h)
                pdf.set_y(pdf.t_margin + logo_max + 1)
            except:
                pass


def _mc_header(pdf, invoice, pw):
    pdf.set_font("Arial", "B", 14)
    pdf.cell(pw, 8, "SOPORTE DE TRANSACCION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Arial", "B", 8)
    doc = _sanitize(str(invoice.get("FTI_DOCUMENTO", "")))
    pdf.cell(pw, 5, f"Numero: {doc}", new_x="LMARGIN", new_y="NEXT")
    fecha = _sanitize(str(invoice.get("FTI_FECHAEMISION", ""))[:10])
    pdf.cell(pw, 5, f"Fecha: {fecha}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)


def _mc_company(pdf, company, pw):
    if not company:
        return
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(pw, 6, "EMISOR", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Arial", "", 7)
    razon = _sanitize(str(company.get("empresa_razon_social") or ""))
    if razon:
        pdf.cell(pw, 4, f"Razon Social: {razon}", new_x="LMARGIN", new_y="NEXT")
    rif = _sanitize(str(company.get("empresa_rif") or ""))
    if rif:
        pdf.cell(pw, 4, f"RIF: {rif}", new_x="LMARGIN", new_y="NEXT")
    dir_emp = _sanitize(str(company.get("empresa_direccion") or ""))
    if dir_emp:
        pdf.cell(pw, 4, f"Direccion: {dir_emp}", new_x="LMARGIN", new_y="NEXT")
    tel_emp = _sanitize(str(company.get("empresa_telefono") or ""))
    if tel_emp:
        pdf.cell(pw, 4, f"Telefono: {tel_emp}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _mc_separator(pdf, pw):
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.ln(2)


def _mc_client(pdf, invoice, client_data, pw):
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(pw, 6, "DATOS DEL CLIENTE", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Arial", "", 7)
    cliente = _sanitize(str(invoice.get("FTI_PERSONACONTACTO") or (client_data.get("FC_DESCRIPCION") if client_data else "") or ""))
    pdf.cell(pw, 4, f"Cliente: {cliente}", new_x="LMARGIN", new_y="NEXT")
    rif = _sanitize(str(invoice.get("FTI_RIFCLIENTE") or ""))
    if rif:
        pdf.cell(pw, 4, f"RIF: {rif}", new_x="LMARGIN", new_y="NEXT")
    dirs = []
    for k in ("FC_DIRECCION1", "FC_DIRECCION2", "FC_DIRECCION3"):
        v = _sanitize(str(client_data.get(k) or ""))
        if v:
            dirs.append(v)
    if dirs:
        pdf.cell(pw, 4, f"Direccion: {', '.join(dirs)}", new_x="LMARGIN", new_y="NEXT")
    tel = _sanitize(str(invoice.get("FTI_TELEFONOCONTACTO") or ""))
    if tel:
        pdf.cell(pw, 4, f"Telefono: {tel}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _mc_detail_table(pdf, detail_lines, pw):
    pdf.set_font("Arial", "B", 9)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(pw, 6, "DETALLE DE LA FACTURA", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    col_w = [6, 12, pw - 6 - 12 - 14 - 16 - 18, 14, 16, 18]
    headers = ["#", "Codigo", "Producto", "Cant.", "P.Unit", "Total"]

    pdf.set_font("Arial", "B", 6)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 5, h, border=1, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()

    pdf.set_font("Arial", "", 6)
    fill = False
    for i, line in enumerate(detail_lines, 1):
        cod = _sanitize(str(line.get("FDI_CODIGO") or ""))
        desc = _sanitize(str(line.get("producto_desc") or line.get("FDI_DESCRIPCIONOFERTA") or ""))
        cant = float(line.get("FDI_CANTIDAD") or 0)
        pcio_bs = _precio_bs(line)
        total = cant * pcio_bs
        pdf.set_fill_color(255, 255, 255)
        if fill:
            pdf.set_fill_color(245, 245, 245)

        desc_w = col_w[2]
        rows_needed = max(1, int(pdf.get_string_width(desc) / max(desc_w, 1)) + 1)
        row_h = max(5, rows_needed * 3.5)

        if pdf.get_y() + row_h > pdf.h - 20:
            pdf.add_page()
            pdf.set_font("Arial", "B", 6)
            pdf.set_fill_color(50, 50, 50)
            pdf.set_text_color(255, 255, 255)
            for h, w in zip(headers, col_w):
                pdf.cell(w, 5, h, border=1, align="C", fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            pdf.set_font("Arial", "", 6)

        pdf.cell(col_w[0], row_h, str(i), border=1, align="C", fill=fill)
        pdf.cell(col_w[1], row_h, cod, border=1, align="C", fill=fill)
        x_desc = pdf.get_x()
        y_desc = pdf.get_y()
        pdf.cell(col_w[2], row_h, "", border=1, fill=fill)
        pdf.set_xy(x_desc, y_desc)
        pdf.multi_cell(col_w[2], 3.5, desc, border=0, align="L")
        pdf.set_xy(x_desc + col_w[2], y_desc)
        pdf.cell(col_w[3], row_h, _fmt(cant), border=1, align="R", fill=fill)
        pdf.cell(col_w[4], row_h, _fmt(pcio_bs), border=1, align="R", fill=fill)
        pdf.cell(col_w[5], row_h, _fmt(total), border=1, align="R", fill=fill)
        pdf.ln()
        fill = not fill
    pdf.ln(2)


def _mc_totals(pdf, invoice, pw):
    label_w = 40
    val_w = 30
    total_neto = float(invoice.get("FTI_TOTALNETO") or 0)
    moneda = int(invoice.get("FTI_MONEDA") or 0)
    factor = float(invoice.get("FTI_FACTORREFERENCIA") or 1)
    if factor == 0:
        factor = 1
    if moneda == 2:
        total_bs = total_neto * factor
    else:
        total_bs = total_neto

    pdf.set_font("Arial", "B", 9)
    pdf.cell(pw - label_w - val_w, 6, "", border=0)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(label_w, 6, "TOTAL:", border=1, align="R", fill=True)
    pdf.cell(val_w, 6, _fmt(total_bs), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")


def _mc_footer(pdf, pw):
    pdf.ln(6)
    y = pdf.get_y()
    pdf.set_draw_color(200, 200, 200)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 7)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(pw, 5, "** SIN DERECHO A CREDITO FISCAL **", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Arial", "I", 6)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(pw, 3, "Enviado desde SmartEnvios", align="C")


# ── TICKET (80 mm) ──
def _generar_ticket(invoice, detail_lines, client_data, company) -> str:
    pdf = FPDF(orientation="P", unit="mm", format=(80, 297))
    pdf.add_font("Arial", "", ARIAL)
    pdf.add_font("Arial", "B", ARIAL_B)
    pdf.add_font("Arial", "I", ARIAL_I)
    pdf.set_auto_page_break(auto=True, margin=8)
    pdf.set_margins(3, 5, 3)
    pdf.add_page()
    pw = pdf.w - 2 * pdf.l_margin

    _tk_watermark(pdf, company)
    _tk_header(pdf, invoice, company, pw)
    _tk_separator(pdf, pw)
    _tk_client(pdf, invoice, client_data, pw)
    _tk_separator(pdf, pw)
    _tk_detail_table(pdf, detail_lines, pw)
    _tk_totals(pdf, invoice, pw)
    _tk_footer(pdf, pw)

    buf = BytesIO()
    pdf.output(buf)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _tk_watermark(pdf, company):
    if company and company.get("incluir_sello", True):
        if os.path.exists(SELLO_PATH):
            try:
                from PIL import Image as PILImage
                img = PILImage.open(SELLO_PATH).convert("RGBA")
                r, g, b, a = img.split()
                a = a.point(lambda x: int(x * 0.08))
                img = PILImage.merge("RGBA", (r, g, b, a))
                buf = BytesIO()
                img.save(buf, format="PNG")
                buf.seek(0)
                with pdf.rotation(35, x=pdf.w / 2, y=pdf.h / 2):
                    pdf.image(buf, x=2, y=pdf.t_margin + 10, w=50)
            except:
                pass


def _tk_header(pdf, invoice, company, pw):
    razon = _sanitize(str(company.get("empresa_razon_social") or "") if company else "")
    if razon:
        pdf.set_font("Arial", "B", 10)
        pdf.cell(pw, 5, razon, align="C", new_x="LMARGIN", new_y="NEXT")
    rif = _sanitize(str(company.get("empresa_rif") or "") if company else "")
    if rif:
        pdf.set_font("Arial", "", 7)
        pdf.cell(pw, 4, f"RIF: {rif}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Arial", "B", 9)
    pdf.cell(pw, 5, "SOPORTE DE TRANSACCION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    pdf.set_font("Arial", "B", 7)
    doc = _sanitize(str(invoice.get("FTI_DOCUMENTO", "")))
    pdf.cell(pw, 4, f"Numero: {doc}", new_x="LMARGIN", new_y="NEXT")
    fecha = _sanitize(str(invoice.get("FTI_FECHAEMISION", ""))[:10])
    pdf.cell(pw, 4, f"Fecha: {fecha}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def _tk_separator(pdf, pw):
    y = pdf.get_y()
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.set_line_width(0.2)
    pdf.ln(2)


def _tk_client(pdf, invoice, client_data, pw):
    pdf.set_font("Arial", "B", 7)
    pdf.cell(pw, 4, "CLIENTE:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "", 7)
    cliente = _sanitize(str(invoice.get("FTI_PERSONACONTACTO") or (client_data.get("FC_DESCRIPCION") if client_data else "") or ""))
    if cliente:
        pdf.cell(pw, 4, cliente, new_x="LMARGIN", new_y="NEXT")
    rif = _sanitize(str(invoice.get("FTI_RIFCLIENTE") or ""))
    if rif:
        pdf.cell(pw, 4, f"RIF: {rif}", new_x="LMARGIN", new_y="NEXT")
    tel = _sanitize(str(invoice.get("FTI_TELEFONOCONTACTO") or ""))
    if tel:
        pdf.cell(pw, 4, f"Tlf: {tel}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def _tk_detail_table(pdf, detail_lines, pw):
    pdf.set_font("Arial", "B", 7)
    pdf.cell(pw, 4, "DETALLE:", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)

    col_w = [5, pw - 5 - 12 - 16 - 18, 12, 16, 18]
    headers = ["#", "Producto", "Cant.", "P.Unit", "Total"]

    pdf.set_font("Arial", "B", 6)
    pdf.set_fill_color(50, 50, 50)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, col_w):
        pdf.cell(w, 4, h, border=1, align="C", fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.ln()

    pdf.set_font("Arial", "", 6)
    fill = False
    for i, line in enumerate(detail_lines, 1):
        desc = _sanitize(str(line.get("producto_desc") or line.get("FDI_DESCRIPCIONOFERTA") or ""))
        cant = float(line.get("FDI_CANTIDAD") or 0)
        pcio_bs = _precio_bs(line)
        total = cant * pcio_bs
        pdf.set_fill_color(255, 255, 255)
        if fill:
            pdf.set_fill_color(245, 245, 245)

        desc_w = col_w[1]
        rows_needed = max(1, int(pdf.get_string_width(desc) / max(desc_w, 1)) + 1)
        row_h = max(4, rows_needed * 3)

        if pdf.get_y() + row_h > pdf.h - 15:
            pdf.add_page()
            pdf.set_font("Arial", "B", 6)
            pdf.set_fill_color(50, 50, 50)
            pdf.set_text_color(255, 255, 255)
            for h, w in zip(headers, col_w):
                pdf.cell(w, 4, h, border=1, align="C", fill=True)
            pdf.set_text_color(0, 0, 0)
            pdf.ln()
            pdf.set_font("Arial", "", 6)

        pdf.cell(col_w[0], row_h, str(i), border=1, align="C", fill=fill)
        x_desc = pdf.get_x()
        y_desc = pdf.get_y()
        pdf.cell(col_w[1], row_h, "", border=1, fill=fill)
        pdf.set_xy(x_desc, y_desc)
        pdf.multi_cell(col_w[1], 3, desc, border=0, align="L")
        pdf.set_xy(x_desc + col_w[1], y_desc)
        pdf.cell(col_w[2], row_h, _fmt(cant), border=1, align="R", fill=fill)
        pdf.cell(col_w[3], row_h, _fmt(pcio_bs), border=1, align="R", fill=fill)
        pdf.cell(col_w[4], row_h, _fmt(total), border=1, align="R", fill=fill)
        pdf.ln()
        fill = not fill
    pdf.ln(2)


def _tk_totals(pdf, invoice, pw):
    total_neto = float(invoice.get("FTI_TOTALNETO") or 0)
    moneda = int(invoice.get("FTI_MONEDA") or 0)
    factor = float(invoice.get("FTI_FACTORREFERENCIA") or 1)
    if factor == 0:
        factor = 1
    if moneda == 2:
        total_bs = total_neto * factor
    else:
        total_bs = total_neto

    pdf.set_font("Arial", "B", 8)
    pdf.cell(pw - 30, 5, "", border=0)
    pdf.set_fill_color(220, 220, 220)
    pdf.cell(12, 5, "TOTAL:", border=1, align="R", fill=True)
    pdf.cell(18, 5, _fmt(total_bs), border=1, align="R", fill=True, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Arial", "", 7)


def _tk_footer(pdf, pw):
    pdf.ln(4)
    pdf.set_draw_color(180, 180, 180)
    pdf.set_line_width(0.3)
    y = pdf.get_y()
    pdf.line(pdf.l_margin, y, pdf.l_margin + pw, y)
    pdf.set_line_width(0.2)
    pdf.ln(2)
    pdf.set_font("Arial", "B", 7)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(pw, 4, "** SIN DERECHO A CREDITO FISCAL **", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Arial", "I", 6)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(pw, 3, "Enviado desde SmartEnvios", align="C")
