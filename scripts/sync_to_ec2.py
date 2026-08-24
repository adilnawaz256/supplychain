#!/usr/bin/env python3
import os
import sys
import time
import subprocess
import paramiko

def sync_and_launch(ip: str, key_file: str):
    print(f"📡 Connecting to EC2 Instance {ip} via SSH...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    connected = False
    for i in range(15):
        try:
            ssh.connect(ip, username='ubuntu', key_filename=key_file, timeout=10)
            connected = True
            print("✅ Connected to EC2!")
            break
        except Exception as e:
            print(f"⏳ Waiting for SSH server readiness (attempt {i+1}/15)...")
            time.sleep(10)
            
    if not connected:
        print("❌ Could not connect via SSH within timeout.")
        return

    # Wait for cloud-init apt lock to release
    print("⏳ Waiting for EC2 system initialization (cloud-init)...")
    stdin, stdout, stderr = ssh.exec_command("sudo cloud-init status --wait")
    print(stdout.read().decode())

    # Install Docker & Docker Compose
    install_cmd = "sudo apt update && sudo apt install -y docker.io docker-compose && sudo systemctl enable --now docker && sudo usermod -aG docker ubuntu"
    print("📦 Installing Docker & Docker Compose on EC2...")
    stdin, stdout, stderr = ssh.exec_command(install_cmd)
    print(stdout.read().decode())
    print(stderr.read().decode())

    # Sync local directory using rsync / scp command
    local_dir = os.path.abspath(".")
    print(f"🔄 Uploading project workspace to EC2 ({ip}:/home/ubuntu/app)...")
    
    # Create remote dir
    ssh.exec_command("mkdir -p /home/ubuntu/app")
    
    rsync_cmd = f"rsync -avz -e 'ssh -i {key_file} -o StrictHostKeyChecking=no' --exclude 'node_modules' --exclude 'venv' --exclude '.git' {local_dir}/ ubuntu@{ip}:/home/ubuntu/app/"
    subprocess.run(rsync_cmd, shell=True)

    # Launch Docker Compose
    print("🚀 Building and starting Docker containers on EC2...")
    stdin, stdout, stderr = ssh.exec_command("cd /home/ubuntu/app && sudo docker-compose down && sudo docker-compose up --build -d")
    print(stdout.read().decode())
    print(stderr.read().decode())

    ssh.close()
    print("🎉 WISUALYST PLATFORM DEPLOYED AND RUNNING ON EC2!")

if __name__ == "__main__":
    ip = sys.argv[1] if len(sys.argv) > 1 else "3.109.122.139"
    key = os.path.abspath("wisualyst-key.pem")
    sync_and_launch(ip, key)
