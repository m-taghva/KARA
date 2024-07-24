import subprocess
from pathlib import Path
import getpass
import yaml

config_file = './configure.conf'  # Path to your YAML configuration file

def generate_ssh_key_for_user(username):
    home_dir = Path(f'/home/{username}')
    ssh_dir = home_dir / '.ssh'
    ssh_key_path = ssh_dir / 'id_rsa'
    # Check if SSH key already exists
    if ssh_key_path.exists():
        print(f"SSH key already exists for {username}.")
        return ssh_key_path
    # Create .ssh directory if it doesn't exist
    ssh_dir.mkdir(mode=0o700, exist_ok=True)
    # Change ownership of the .ssh directory
    subprocess.run(['chown', '-R', f'{username}:{username}', ssh_dir], check=True)
    # Generate SSH key
    subprocess.run(['sudo', '-u', username, 'ssh-keygen', '-t', 'rsa', '-b', '2048', '-f', str(ssh_key_path), '-N', ''], check=True)
    print(f"SSH key generated for {username} at {ssh_key_path}")
    return ssh_key_path

def copy_ssh_key_to_servers(key_path, servers, username):
    public_key_path = str(key_path) + '.pub'
    if not Path(public_key_path).exists():
        print("Public key not found.")
        return
    for server, details in servers.items():
        ip = details['ip_swift']
        port = details.get('ssh_port')
        print(f"Copying SSH key to {ip} (port {port})...")
        password = getpass.getpass(f"Enter password for {username}@{ip}: ")
        try:
            subprocess.run(f"ssh-copy-id -p {port} {username}@{ip}", shell=True, check=True)
            print(f"SSH key copied to {ip}")
        except subprocess.CalledProcessError as e:
            print(f"Failed to copy SSH key to {ip}: {e}")

if __name__ == "__main__":
    # Load configuration from the YAML file
    with open(config_file, 'r') as file:
        config = yaml.safe_load(file)
    username = config['ssh_info']['master_user']
    servers = {key: value for key, value in config['ssh_info'].items() if key != 'master_user'}
    key_path = generate_ssh_key_for_user(username)
    copy_ssh_key_to_servers(key_path, servers, username)
