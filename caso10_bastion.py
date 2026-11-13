from conexao import conectar, executar

# Configuração do servidor intermediário (Jump Host / Bastion)
BASTION = {
    "nome": "BASTION",
    "host": "127.0.0.1",
    "porta": 22,
    "usuario": "bastion",
}

# Configuração do equipamento interno acessível apenas via Bastion na porta 2222
EQUIPAMENTO_INTERNO = {
    "nome": "R1-INTERNO",
    "host": "127.0.0.1",
    "porta": 2222,
    "usuario": "r1",
}


def acessar_via_bastion(bastion_cfg: dict, interno_cfg: dict) -> None:
    cliente_bastion = None
    canal_tunel = None
    cliente_interno = None

    try:
        # 1. Conecta ao servidor intermediário (Bastion) na porta 22
        print(f"[1/4] Conectando ao Jump Host ({bastion_cfg['usuario']}@{bastion_cfg['host']}:{bastion_cfg['porta']})...")
        cliente_bastion = conectar(bastion_cfg)
        print("      -> Conexão com Bastion estabelecida.")

        # 2. Abre um canal de encaminhamento TCP (direct-tcpip) do Bastion até o equipamento interno
        transporte_bastion = cliente_bastion.get_transport()
        destino = (interno_cfg["host"], interno_cfg["porta"])
        origem = ("127.0.0.1", 0)

        print(f"[2/4] Abrindo túnel SSH através do Bastion até {destino[0]}:{destino[1]}...")
        canal_tunel = transporte_bastion.open_channel("direct-tcpip", destino, origem)
        print("      -> Túnel TCP aberto com sucesso.")

        # 3. Autentica como 'r1' no equipamento interno usando o túnel como socket (sock)
        print(f"[3/4] Autenticando como '{interno_cfg['usuario']}' no equipamento interno...")
        cliente_interno = conectar(interno_cfg, sock=canal_tunel)
        print("      -> Autenticado no equipamento interno!")

        # 4. Executa comandos e comprova que o tráfego passou pelo Bastion
        print("[4/4] Executando comandos e validando o caminho do tráfego:\n")

        _, out_host, _ = executar(cliente_interno, "hostname")
        _, out_user, _ = executar(cliente_interno, "whoami")
        _, out_conn, _ = executar(cliente_interno, "echo $SSH_CONNECTION")

        # Variável SSH_CONNECTION mostra: <IP_ORIGEM> <PORTA_ORIGEM> <IP_DESTINO> <PORTA_DESTINO>
        partes_conn = out_conn.strip().split()
        porta_destino = partes_conn[3] if len(partes_conn) >= 4 else "desconhecida"

        print(f"  Hostname remoto : {out_host.strip()}")
        print(f"  Usuário ativo   : {out_user.strip()}")
        print(f"  SSH_CONNECTION  : {out_conn.strip()}")
        print(f"  Túnel ativo     : {canal_tunel.active} (Origem: {canal_tunel.origin_addr} -> Destino: {canal_tunel.getpeername()})")

        if porta_destino == str(interno_cfg["porta"]) and canal_tunel.active:
            print("\n[COMPROVAÇÃO] Sucesso! O tráfego entrou na porta interna 2222 encapsulado pelo túnel do Bastion.")

    except Exception as erro:
        print(f"\n[ERRO] Falha na conexão via Bastion: {erro}")
    finally:
        # Fecha as conexões na ordem inversa (interno -> túnel -> bastion)
        if cliente_interno:
            cliente_interno.close()
        if canal_tunel:
            canal_tunel.close()
        if cliente_bastion:
            cliente_bastion.close()


if __name__ == "__main__":
    acessar_via_bastion(BASTION, EQUIPAMENTO_INTERNO)
