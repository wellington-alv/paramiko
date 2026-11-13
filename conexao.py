import os
import paramiko


def conectar(disp, sock=None):
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    # Busca a chave id_redes gerada anteriormente, se existir
    chave_padrao = os.path.expanduser("~/.ssh/id_redes")
    chave = disp.get("chave") or (chave_padrao if os.path.exists(chave_padrao) else None)
    
    # Busca a senha no dicionário ou na variável de ambiente SSH_SENHA
    senha = disp.get("senha") or os.environ.get("SSH_SENHA", "Redes@2026")

    cliente.connect(
        hostname=disp["host"],
        port=disp.get("porta", 22),
        username=disp["usuario"],
        password=senha,
        key_filename=chave,
        sock=sock,
    )
    return cliente


def executar(cliente, comando):
    """Executa um único comando via SSH e retorna (status, stdout, stderr)."""
    stdin, stdout, stderr = cliente.exec_command(comando)
    status = stdout.channel.recv_exit_status()
    saida = stdout.read().decode(errors="ignore")
    erro = stderr.read().decode(errors="ignore")
    return status, saida, erro
