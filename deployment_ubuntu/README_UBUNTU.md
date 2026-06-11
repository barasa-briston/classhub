# Cisco Canvas LMS - Ubuntu Deployment Guide

This guide ensures the LMS is correctly mapped to `ciscocanvas.chuka.ac.ke` using your reserved IP.

## 📌 Network Blueprint

- **LMS Domain**: `ciscocanvas.chuka.ac.ke`
- **Main Website**: `cisco.chuka.ac.ke` (Redirection Source)
- **Official Email**: `cisco@chuka.ac.ke`

## 1. Automated Setup

1. Transfer the project to `/home/ubuntu/lms`.
2. Run the installer:

   ```bash
   cd deployment_ubuntu
   chmod +x setup.sh
   ./setup.sh
   ```

## 2. Environment Configuration

Create a `.env` file in the root directory (`/home/ubuntu/lms/.env`) using the provided example:

```bash
cp deployment_ubuntu/.env.example .env
nano .env
# Set DJANGO_DEBUG=False and add your SECRET_KEY
```

## 3. Nginx Configuration

The `lms.nginx` file is pre-configured for `ciscocanvas.chuka.ac.ke`.
To apply it:

```bash
sudo cp lms.nginx /etc/nginx/sites-available/lms
sudo ln -s /etc/nginx/sites-available/lms /etc/nginx/sites-enabled
sudo nginx -t
sudo systemctl restart nginx
```

## 4. SSL (HTTPS)

Secure the subdomain once the DNS A Record is active:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d ciscocanvas.chuka.ac.ke
```

## 5. Production Checklist

In `lms/lms/config/settings.py`:

- Set `DEBUG = False`
- Add `ciscocanvas.chuka.ac.ke` to `ALLOWED_HOSTS`.
- Ensure `DEFAULT_FROM_EMAIL` matches `cisco@chuka.ac.ke`.
