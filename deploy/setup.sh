#!/usr/bin/env bash
# One-time setup of a fresh Ubuntu 24.04 server for Trot Dynasty. Run as root, once:
#   bash setup.sh trotdynasty.com
# Installs Python 3.14 (the version the game and its save were made with), Pillow and NumPy; the Caddy web server for
# HTTPS (certificates are automatic); a firewall that only lets in SSH and web traffic; the game as a service that starts
# on boot and restarts if it stops; and a nightly backup of the save. The game itself is copied up by push.ps1.
set -euo pipefail
DOMAIN="${1:?usage: bash setup.sh your-domain.com}"
APP=/opt/trotdynasty
export DEBIAN_FRONTEND=noninteractive NEEDRESTART_MODE=a   # no questions mid-install

apt-get update
apt-get -y upgrade
apt-get -y install curl debian-keyring debian-archive-keyring apt-transport-https ufw

# firewall: SSH and the web only
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# the game's own user, with no login of its own
id trot >/dev/null 2>&1 || useradd --system --create-home --home-dir "$APP" --shell /usr/sbin/nologin trot
mkdir -p "$APP" /var/backups/trotdynasty
chown -R trot:trot "$APP" /var/backups/trotdynasty

# Python 3.14 and the two libraries, in the game's own environment (uv installs the exact Python version)
curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR=/usr/local/bin sh
KIT="$(cd "$(dirname "$0")" && pwd)"   # this folder, before moving to the game's own (uv reads config from where it runs)
cd "$APP"
sudo -u trot env HOME="$APP" UV_NO_CONFIG=1 uv venv --allow-existing --python 3.14 "$APP/venv"
sudo -u trot env HOME="$APP" UV_NO_CONFIG=1 uv pip install --python "$APP/venv/bin/python" pillow numpy

# Caddy: HTTPS in front of the game
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | gpg --batch --yes --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' > /etc/apt/sources.list.d/caddy-stable.list
apt-get update
apt-get -y install caddy
sed "s/{DOMAIN}/$DOMAIN/" "$KIT/Caddyfile" > /etc/caddy/Caddyfile
systemctl reload caddy

# the game as a service, and the nightly backup
cp "$KIT/trotdynasty.service" /etc/systemd/system/
cp "$KIT/backup.sh" /usr/local/bin/trotdynasty-backup
chmod +x /usr/local/bin/trotdynasty-backup
echo "15 4 * * * root /usr/local/bin/trotdynasty-backup" > /etc/cron.d/trotdynasty-backup
systemctl daemon-reload
systemctl enable trotdynasty

echo "Setup done. Now push the game from your PC with push.ps1, and it will start."
