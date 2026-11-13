import os
import paramiko


def conectar(disp, timeout=10, sock=None):
    """Abre uma conexão SSH com o dispositivo descrito no inventário."""
    cliente = paramiko.SSHClient()
    cliente.load_system_host_keys()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cliente.connect(
        hostname=disp["host"],
        port=disp.get("porta", 22),
        username=disp["usuario"],
        password=os.environ.get("SSH_SENHA"),
        key_filename=disp.get("chave"),
        timeout=timeout,
        banner_timeout=timeout,
        auth_timeout=timeout,
        look_for_keys=False,
        allow_agent=False,
        sock=sock,
    )
    return cliente


def executar(cliente, comando, timeout=15):
    """Executa um comando e devolve (código_de_saída, saída, erro)."""
    _, out, err = cliente.exec_command(comando, timeout=timeout)
    saida = out.read().decode().strip()
    erro = err.read().decode().strip()
    codigo = out.channel.recv_exit_status()
    return codigo, saida, erro