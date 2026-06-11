import os
from xhtml2pdf import pisa

def convert_html_to_pdf(source_html, output_filename):
    with open(output_filename, "w+b") as result_file:
        pisa_status = pisa.CreatePDF(source_html, dest=result_file)
    return pisa_status.err

if __name__ == "__main__":
    sop_content = """
    <html>
    <head>
    <style>
        body { font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.6; }
        h1 { color: #2c3e50; text-align: center; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; }
        h2 { color: #e67e22; border-bottom: 1px solid #ddd; margin-top: 20px; }
        h3 { color: #2980b9; }
        code { background-color: #f4f4f4; padding: 2px 5px; font-family: Courier, monospace; }
        pre { background-color: #f4f4f4; padding: 10px; border: 1px solid #ddd; word-wrap: break-word; }
        .footer { text-align: center; font-size: 10px; margin-top: 50px; color: #777; }
        .highlight { color: #c0392b; font-weight: bold; }
    </style>
    </head>
    <body>
        <h1>Ubuntu Deployment SOP (Cisco Canvas LMS)</h1>
        <p align="center"><b>Target URL:</b> ciscocanvas.chuka.ac.ke | <b>Admin Email:</b> cisco@chuka.ac.ke</p>

        <div class="section">
            <h2>1. Primary Network Identity</h2>
            <ul>
                <li><b>LMS Subdomain:</b> <code>ciscocanvas.chuka.ac.ke</code> (Points to Server IP)</li>
                <li><b>Main Website:</b> <code>cisco.chuka.ac.ke</code> (Will redirect to LMS)</li>
                <li><b>Institutional Email:</b> <code>cisco@chuka.ac.ke</code></li>
            </ul>
        </div>

        <div class="section">
            <h2>2. Server Environment Setup</h2>
            <p>Ensure files are at <code>/home/ubuntu/lms</code> and run the automated setup:</p>
            <pre>
cd /home/ubuntu/lms/deployment_ubuntu
bash setup.sh
            </pre>
        </div>

        <div class="section">
            <h2>3. Nginx Reverse Proxy (DNS Mapping)</h2>
            <p>Deploy the Nginx configuration to map the reserved IP to the LMS domain:</p>
            <pre>
sudo cp lms.nginx /etc/nginx/sites-available/lms
sudo ln -s /etc/nginx/sites-available/lms /etc/nginx/sites-enabled
sudo nginx -t && sudo systemctl restart nginx
            </pre>
        </div>

        <div class="section">
            <h2>4. Essential Production Adjustments</h2>
            <p>Before going live, verify <code>lms/lms/config/settings.py</code> has these values:</p>
            <pre>
DEBUG = False
ALLOWED_HOSTS = ["ciscocanvas.chuka.ac.ke", "RESERVED_IP"]
CSRF_TRUSTED_ORIGINS = ["https://ciscocanvas.chuka.ac.ke"]
            </pre>
        </div>

        <div class="section">
            <h2>5. SSL Security (Let's Encrypt)</h2>
            <p>Apply SSL specifically to the subdomain:</p>
            <pre>
sudo certbot --nginx -d ciscocanvas.chuka.ac.ke
            </pre>
        </div>

        <div class="footer">
            <p>2026 &copy; CISCO Network Academy - Chuka University</p>
        </div>
    </body>
    </html>
    """
    
    output_pdf = "LMS_Ubuntu_Deployment_SOP.pdf"
    error = convert_html_to_pdf(sop_content, output_pdf)
    if not error:
        print(f"Successfully generated {output_pdf}")
    else:
        print(f"Error generating PDF: {error}")
