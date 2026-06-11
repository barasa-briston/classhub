
import csv
from django.http import HttpResponse
from django.template.loader import get_template
from xhtml2pdf import pisa
from io import BytesIO

def render_to_pdf(template_src, context_dict={}, filename=None):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("utf-8")), result, encoding='utf-8')
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        if filename:
             response['Content-Disposition'] = f'inline; filename="{filename}"'
        else:
             response['Content-Disposition'] = 'inline'
        return response
    return None

def export_to_csv(queryset, filename, fields, headers):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(headers)
    
    for obj in queryset:
        row = []
        for field in fields:
            # Handle recursive attributes like 'student.username'
            value = obj
            for attr in field.split('.'):
                if hasattr(value, attr):
                    value = getattr(value, attr)
                    if callable(value):
                        value = value()
                else:
                    value = ""
                    break
            row.append(str(value))
        writer.writerow(row)
        
    return response
