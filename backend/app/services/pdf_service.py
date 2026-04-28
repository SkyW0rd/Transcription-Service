from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas


class PDFService:
    _fonts_ready = False
    _regular_font_name = "Helvetica"
    _bold_font_name = "Helvetica-Bold"

    def _ensure_fonts(self) -> tuple[str, str]:
        if self._fonts_ready:
            return self._regular_font_name, self._bold_font_name

        candidates = [
            (
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ),
            (
                Path("/usr/share/fonts/dejavu/DejaVuSans.ttf"),
                Path("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf"),
            ),
        ]

        for regular_path, bold_path in candidates:
            if regular_path.exists() and bold_path.exists():
                pdfmetrics.registerFont(TTFont("DejaVuSans", str(regular_path)))
                pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", str(bold_path)))
                self._regular_font_name = "DejaVuSans"
                self._bold_font_name = "DejaVuSans-Bold"
                self._fonts_ready = True
                return self._regular_font_name, self._bold_font_name

        raise RuntimeError(
            "Unicode fonts for PDF are not available. "
            "Install DejaVuSans fonts in container (fonts-dejavu-core)."
        )

    def generate_pdf(
        self,
        output_path: Path,
        job_id: str,
        summary_text: str,
        transcript_text: str,
        original_filename: str,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        regular_font, bold_font = self._ensure_fonts()

        pdf = canvas.Canvas(str(output_path), pagesize=A4)
        width, height = A4

        y = height - 40

        pdf.setFont(bold_font, 16)
        pdf.drawString(40, y, "Отчёт по транскрибации")
        y -= 30

        pdf.setFont(regular_font, 11)
        pdf.drawString(40, y, f"Job ID: {job_id}")
        y -= 20
        pdf.drawString(40, y, f"Файл: {original_filename}")
        y -= 30

        pdf.setFont(bold_font, 13)
        pdf.drawString(40, y, "Summary")
        y -= 20

        pdf.setFont(regular_font, 10)
        for line in summary_text.splitlines():
            pdf.drawString(40, y, line[:110])
            y -= 14
            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont(regular_font, 10)

        y -= 10
        pdf.setFont(bold_font, 13)
        pdf.drawString(40, y, "Transcript")
        y -= 20

        pdf.setFont(regular_font, 9)
        for line in transcript_text.splitlines():
            pdf.drawString(40, y, line[:120])
            y -= 12
            if y < 50:
                pdf.showPage()
                y = height - 40
                pdf.setFont(regular_font, 9)

        pdf.save()
        return output_path


pdf_service = PDFService()