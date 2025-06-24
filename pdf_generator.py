# pdf_generator.py

import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

def generate_assignment_pdf(a_id, worker, order, assign_date, pdf_dir):
    filename = f"assignment_{a_id}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 50, "Work Assignment Slip")

    c.setFont("Helvetica", 12)
    c.drawString(50, height - 90,  f"Assignment ID : {a_id}")
    c.drawString(50, height - 110, f"Assign Date   : {assign_date}")

    c.drawString(50, height - 150, "— Worker Details —")
    c.drawString(70, height - 170, f"ID       : {worker['id']}")
    c.drawString(70, height - 190, f"Name     : {worker['name']}")
    c.drawString(70, height - 210, f"Contact  : {worker.get('contact_number', '-')}")

    c.drawString(50, height - 250, "— Order Details —")
    c.drawString(70, height - 270, f"Order ID   : {order['id']}")
    c.drawString(70, height - 290, f"Customer   : {order['customer_name']}")
    c.drawString(70, height - 310, f"Sofa Type  : {order['sofa_type']}")
    c.drawString(70, height - 330, f"Quantity   : {order['quantity']}")

    c.drawString(50, height - 370, "Please complete the work as per schedule.")
    c.save()

    return filename
