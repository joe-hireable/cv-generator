import requests

class HireableClient:
    def docx_to_pdf(self, request):
        files = {
            'file': ("doc.docx", request, 'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        }
        response = requests.post("https://docx2pdf.tombrown.io/convert", files=files, timeout=60)
        return response