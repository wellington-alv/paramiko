# caso04_shell_interativo.py
import time

from conexao import conectar, executar

dispositivo = {"nome": "R1", "host": "127.0.0.1", "usuario": "r1"}


def ler(canal, pausa=0.6):
    """Aguarda e lê tudo o que o equipamento enviou."""
    time.sleep(pausa)
    dados = ""
    while canal.recv_ready():
        dados += canal.recv(65535).decode(errors="ignore")
        time.sleep(0.1)
    return dados


sequencia = ["cd /tmp", "pwd", "export AMBIENTE=PRODUCAO", "echo $AMBIENTE"]

cliente = conectar(dispositivo)
try:
    print("=== SESSAO INTERATIVA (invoke_shell) ===")
    canal = cliente.invoke_shell()
    ler(canal)                      # descarta o banner inicial
    for cmd in sequencia:
        canal.send(cmd + "\n")
        print(ler(canal))
    canal.close()

    print("=== UM COMANDO POR CHAMADA (exec_command) ===")
    for cmd in sequencia:
        _, saida, _ = executar(cliente, cmd)
        print(f"${cmd} ->{saida!r}")
finally:
    cliente.close()