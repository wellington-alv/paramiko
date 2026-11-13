import difflib
from pathlib import Path
from conexao import conectar, executar

DISPOSITIVOS = [
    {"nome": "R1", "host": "127.0.0.1", "usuario": "r1"},
    {"nome": "R2", "host": "127.0.0.1", "usuario": "r2"},
    {"nome": "R3", "host": "127.0.0.1", "usuario": "r3"},
]

ARQUIVO_REFERENCIA = Path("referencia.cfg")
ARQUIVO_REMOTO = "dispositivo.cfg"

CONTEUDO_PADRAO_REF = """ntp_server = 10.0.0.50
snmp_community = REDE_SEGURA_2026
ssh_timeout = 300
banner_login = Acesso restrito a administradores autorizados
logging_host = 10.0.0.100
"""


def garantir_referencia_local(caminho: Path) -> list[str]:
    """Cria o referencia.cfg se não existir e retorna suas linhas limpas."""
    if not caminho.exists():
        with caminho.open("w", encoding="utf-8", newline="\n") as f:
            f.write(CONTEUDO_PADRAO_REF)
        print(f"[LOCAL] Arquivo de referência '{caminho}' criado.")

    with caminho.open("r", encoding="utf-8") as f:
        return [linha.strip() for linha in f.readlines() if linha.strip()]


def auditar_dispositivo(disp: dict, linhas_referencia: list[str]) -> str:
    """Lê a configuração remota via sftp.open e compara com a referência."""
    nome = disp["nome"]
    cliente = None
    sftp = None

    try:
        cliente = conectar(disp)

        # Descobre o caminho absoluto do home remoto
        _, home_remoto, _ = executar(cliente, "pwd")
        caminho_remoto = f"{home_remoto.strip()}/{ARQUIVO_REMOTO}"

        # Lê o arquivo remoto diretamente em memória sem gravar no disco local
        sftp = cliente.open_sftp()
        with sftp.open(caminho_remoto, "r") as arquivo_remoto:
            conteudo_remoto = arquivo_remoto.read().decode("utf-8", errors="ignore")

        # Filtra a linha 'hostname' (única de cada equipamento) e linhas vazias
        linhas_remotas = [
            linha.strip()
            for linha in conteudo_remoto.splitlines()
            if linha.strip() and not linha.strip().startswith("hostname")
        ]

        # Compara o padrão esperado com o arquivo do equipamento
        diferencas = list(
            difflib.unified_diff(
                linhas_referencia,
                linhas_remotas,
                fromfile="referencia.cfg",
                tofile=f"{nome}:{ARQUIVO_REMOTO}",
                lineterm="",
            )
        )

        if not diferencas:
            print(f"[{nome}] Status: CONFORME")
            return "CONFORME"

        print(f"[{nome}] Status: NÃO CONFORME")
        print(f"[{nome}] Relatório de divergências (Configuration Drift):")
        for linha_diff in diferencas:
            print(f"    {linha_diff}")
        return "NÃO CONFORME"

    except FileNotFoundError:
        print(f"[{nome}] Status: NÃO CONFORME (Arquivo '{ARQUIVO_REMOTO}' ausente)")
        return "NÃO CONFORME"
    except Exception as erro:
        print(f"[{nome}] ERRO na auditoria: {erro}")
        return "ERRO"
    finally:
        if sftp:
            sftp.close()
        if cliente:
            cliente.close()


if __name__ == "__main__":
    linhas_padrao = garantir_referencia_local(ARQUIVO_REFERENCIA)
    resumo = {}

    print("=== INICIANDO AUDITORIA DE CONFORMIDADE (CONFIGURATION DRIFT) ===\n")
    for dispositivo in DISPOSITIVOS:
        status = auditar_dispositivo(dispositivo, linhas_padrao)
        resumo[dispositivo["nome"]] = status
        print("-" * 60)

    print("\n=== RESUMO EXECUTIVO ===")
    for eqp, st in resumo.items():
        print(f"  {eqp:<5} -> {st}")
