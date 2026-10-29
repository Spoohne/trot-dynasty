# Moving Trot Dynasty to its own server

## What you do (needs your accounts and payment)

1. **DigitalOcean account:** sign up at digitalocean.com.
2. **SSH key:** run `ssh-keygen -t ed25519` in PowerShell on this PC and press Enter through the questions. Open
   `C:\Users\spooh\.ssh\id_ed25519.pub` in Notepad and copy its one line. Never share the file without `.pub`.
3. **Create a Droplet** (DigitalOcean's name for a server):
   - Ubuntu 24.04 LTS, Basic plan, Regular CPU, **$12/mo (2 GB RAM)**.
   - Region: **New York**. Race night runs on Eastern time, and players are near.
   - Authentication: **SSH key**, adding the line you copied.
   - Tick **Backups** (weekly whole-server copies, about $2.40/mo).
   - Note its IP address.
4. **Buy a domain**, e.g. at Namecheap or Cloudflare. In its DNS settings, add two **A records** pointing at the
   Droplet's IP: `@` and `www`.
5. Send Claude the IP and the domain.

## What Claude does (or you, from this folder)

1. Copy this folder up and run setup once: `scp -r deploy root@IP:/root/` then `ssh root@IP "bash /root/deploy/setup.sh yourdomain.com"`.
2. On race-night-free time, stop the game on this PC, then move everything across:
   `.\deploy\push.ps1 -Server IP -WithSave`
3. Check `https://yourdomain.com` works. Everyone re-adds the home-screen icon from the new address and logs in with
   their same name and password.
4. Later code updates: `.\deploy\push.ps1 -Server IP` (keeps the server's save).

## Running it

- The game starts on boot and restarts itself if it stops.
- Logs: `ssh root@IP journalctl -u trotdynasty -f`.
- Nightly save copies (the last 14) are in `/var/backups/trotdynasty`. DigitalOcean's weekly backups cover the whole
  server.
- Race night runs on the server's clock at 8 PM Eastern, so this PC can sleep.
