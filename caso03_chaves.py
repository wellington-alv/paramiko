import os
import subprocess
import paramiko

# 1. Define o caminho da chave na pasta do usuário
pasta_ssh = os.path.expanduser("~/.ssh")
os.makedirs(pasta_ssh, exist_ok=True)
caminho_chave = os.path.join(pasta_ssh, "id_redes")

# 2. Gera a chave ed25519 (se ainda não existir)
if not os.path.exists(caminho_chave):
    subprocess.run([
        "ssh-keygen", "-t", "ed25519",
        "-f", caminho_chave,
        "-C", "gerente-redes",
        "-N", ""
    ], check=True)

# 3. Lê o conteúdo da chave pública
with open(f"{caminho_chave}.pub", "r") as arquivo:
    chave_publica = arquivo.read().strip()

# 4. Pega a senha da variável de ambiente SSH_SENHA
usuarios = ["r1", "r2", "r3"]
senha_inicial = os.environ.get("SSH_SENHA", "Redes@2026")

for u in usuarios:
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        # look_for_keys=False e allow_agent=False evitam que o Paramiko tente outras chaves antes da senha
        cliente.connect(
            "127.0.0.1",
            username=u,
            password=senha_inicial,
            look_for_keys=False,
            allow_agent=False
        )
        comando = (
            f"mkdir -p ~/.ssh && "
            f"echo '{chave_publica}' >> ~/.ssh/authorized_keys && "
            f"chmod 700 ~/.ssh && chmod 600 ~/.ssh/authorized_keys"
        )
        stdin, stdout, stderr = cliente.exec_command(comando)
        stdout.channel.recv_exit_status()  # Aguarda o comando terminar antes de fechar
        print(f"Chave instalada com sucesso para {u}!")
    except Exception as e:
        print(f"Erro ao conectar em {u}: {e}")
    finally:
        cliente.close()
