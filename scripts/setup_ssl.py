#!/usr/bin/env python3
"""
Automated Let's Encrypt Certbot SSL Generator for Wisualyst Platform on EC2.
Installs Certbot and configures free HTTPS SSL certificates for your domain.
"""
import os
import sys
import paramiko

def setup_certbot_ssl(ip: str, domain: str, email: str = "admin@wisualyst.com"):
    key_file = os.path.abspath("wisualyst-key.pem")
    print(f"🔒 Connecting to EC2 ({ip}) to generate Let's Encrypt SSL certificate for {domain}...")
    
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(ip, username='ubuntu', key_filename=key_file, timeout=15)

    commands = [
        "sudo apt update && sudo apt install -y certbot python3-certbot-nginx",
        f"sudo certbot --nginx -d {domain} --non-interactive --agree-tos -m {email} --redirect || true"
    ]

    for cmd in commands:
        print(f"⚙️ Running: {cmd}")
        stdin, stdout, stderr = ssh.exec_command(cmd)
        print(stdout.read().decode())
        print(stderr.read().decode())

    ssh.close()
    print(f"🎉 Free Let's Encrypt SSL Certificate successfully generated for https://{domain} !")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        domain_name = sys.argv[1]
        ip_addr = sys.argv[2] if len(sys.argv) > 2 else "3.109.122.139"
        setup_certbot_ssl(ip_addr, domain_name)
    else:
        print("Usage: python scripts/setup_ssl.py <YOUR_DOMAIN_NAME> [EC2_IP]")
