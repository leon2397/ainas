Name:           aiqizhi
Version:        @VERSION@
Release:        @RELEASE@%{?dist}
Summary:        AIqizhi - AI-powered NAS Media Management System

License:        MIT
URL:            https://github.com/aiqizhi/ai-nas-media-manager
Source0:        aiqizhi-%{version}.tar.gz

BuildArch:      noarch

Requires:       python3 >= 3.8
Requires:       python3-pip
Requires:       ffmpeg

%description
AIqizhi is an intelligent media management system designed for
NAS devices and Linux servers. It features AI-powered auto-classification,
face recognition, multi-device management, web dashboard and mobile H5.

Key Features:
  - AI auto-classification (CPU/GPU/NPU adaptive)
  - Face recognition engine
  - Multi-storage backend (Local/SSH/SMB/NAS)
  - Multi-device management with heartbeat monitoring
  - RESTful API with JWT authentication
  - Web dashboard + Mobile H5 responsive UI
  - Plugin system for extensibility
  - Docker and Kubernetes deployment support

%prep
%setup -q

%install
# Application files
mkdir -p %{buildroot}/opt/aiqizhi
cp -r backend %{buildroot}/opt/aiqizhi/
cp -r frontend %{buildroot}/opt/aiqizhi/
cp -r config %{buildroot}/opt/aiqizhi/
cp -r arm %{buildroot}/opt/aiqizhi/

# Systemd service
mkdir -p %{buildroot}/etc/systemd/system
install -m 0644 packaging/aiqizhi.service %{buildroot}/etc/systemd/system/

# Logrotate
mkdir -p %{buildroot}/etc/logrotate.d
install -m 0644 packaging/aiqizhi.logrotate %{buildroot}/etc/logrotate.d/aiqizhi

# Environment file
mkdir -p %{buildroot}/etc/aiqizhi
install -m 0644 packaging/aiqizhi.conf %{buildroot}/etc/aiqizhi/

# Data directories
mkdir -p %{buildroot}/var/lib/aiqizhi/media
mkdir -p %{buildroot}/var/lib/aiqizhi/thumbnails
mkdir -p %{buildroot}/var/lib/aiqizhi/database
mkdir -p %{buildroot}/var/log/aiqizhi

%post
# Create system user
if ! id aiqizhi >/dev/null 2>&1; then
    useradd --system --home-dir /opt/aiqizhi --shell /usr/sbin/nologin         --comment "AIqizhi Media Manager" aiqizhi
fi

# Create Python venv
python3 -m venv /opt/aiqizhi/backend/venv

# Install dependencies
if [ -f /opt/aiqizhi/backend/requirements.txt ]; then
    /opt/aiqizhi/backend/venv/bin/pip install --no-cache-dir --quiet         -r /opt/aiqizhi/backend/requirements.txt 2>/dev/null || {
        if [ -f /opt/aiqizhi/backend/requirements-min.txt ]; then
            /opt/aiqizhi/backend/venv/bin/pip install --no-cache-dir --quiet                 -r /opt/aiqizhi/backend/requirements-min.txt 2>/dev/null || true
        fi
    }
fi

# Init database + create admin
cd /opt/aiqizhi/backend
ADMIN_PASS=$(/opt/aiqizhi/backend/venv/bin/python -c "
import sys, secrets, string
sys.path.insert(0, '.')
try:
    from database.db import Database
    from core.auth import AuthManager
    db = Database()
    db.init_tables()
    auth = AuthManager()
    pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    auth.create_user('admin', pw, 'admin')
    print(pw)
except Exception:
    pw = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16))
    print(pw)
") || { ADMIN_PASS=$(head -c 48 /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 16); }

echo "admin:$ADMIN_PASS" > /etc/aiqizhi/.admin_password
chmod 600 /etc/aiqizhi/.admin_password

# Generate default config
if [ ! -f /etc/aiqizhi/config.yaml ]; then
    SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "0.0.0.0")
    JWT_SECRET=$(/opt/aiqizhi/backend/venv/bin/python -c "import secrets; print(secrets.token_hex(32))")
    cat > /etc/aiqizhi/config.yaml << YAMLEOF
server:
  host: "0.0.0.0"
  port: 18000
  workers: 2
database:
  path: "/var/lib/aiqizhi/database/aiqizhi.db"
media:
  base_path: "/var/lib/aiqizhi/media"
  thumbnail_path: "/var/lib/aiqizhi/thumbnails"
  max_upload_size: 5368709120
auth:
  jwt_secret: "$JWT_SECRET"
  token_expire_hours: 72
logging:
  level: "INFO"
  file: "/var/log/aiqizhi/aiqizhi.log"
  max_size: 52428800
  backup_count: 5
YAMLEOF
fi

# Set permissions
chown -R aiqizhi:aiqizhi /opt/aiqizhi /var/lib/aiqizhi /var/log/aiqizhi /etc/aiqizhi
chmod 755 /opt/aiqizhi
chmod 700 /etc/aiqizhi

# Start service
systemctl daemon-reload
systemctl enable aiqizhi
systemctl start aiqizhi

SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "YOUR_SERVER_IP")
sleep 2

echo ""
echo "======================================================"
echo "     AIqizhi Media Manager - Install Complete"
echo "======================================================"
echo "  URL:      http://${SERVER_IP}:18000"
echo "  Username: admin"
echo "  Password: ${ADMIN_PASS}"
echo "  Saved to: /etc/aiqizhi/.admin_password"
echo "======================================================"

%preun
if [ $1 -eq 0 ]; then
    systemctl stop aiqizhi 2>/dev/null || true
    systemctl disable aiqizhi 2>/dev/null || true
fi

%postun
if [ $1 -eq 0 ]; then
    userdel aiqizhi 2>/dev/null || true
    rm -rf /var/lib/aiqizhi /var/log/aiqizhi /etc/aiqizhi
    rm -f /etc/systemd/system/aiqizhi.service /etc/logrotate.d/aiqizhi
    systemctl daemon-reload
fi

%files
%defattr(-,aiqizhi,aiqizhi,-)
/opt/aiqizhi/backend
/opt/aiqizhi/frontend
/opt/aiqizhi/config
/opt/aiqizhi/arm
%attr(0644,root,root) /etc/systemd/system/aiqizhi.service
%attr(0644,root,root) /etc/logrotate.d/aiqizhi
%attr(0644,root,root) /etc/aiqizhi/aiqizhi.conf
%attr(0750,aiqizhi,aiqizhi) /var/lib/aiqizhi
%attr(0750,aiqizhi,aiqizhi) /var/log/aiqizhi

%changelog
* Wed Apr 08 2026 AIqizhi Team <support@aiqizhi.com> - 2.0.0-1
- New release: Storage plugin architecture fix
- DEB/RPM packaging support
- One-click installer
