import ipaddress
import re
from conexao import conectar, executar

# Lista de dispositivos da rede (ajuste o caminho do arquivo conforme seu laboratório)
DISPOSITIVOS = [
    {"nome": "R1", "host": "127.0.0.1", "usuario": "r1"},
    {"nome": "R2", "host": "127.0.0.1", "usuario": "r2"},
    {"nome": "R3", "host": "127.0.0.1", "usuario": "r3"},
]

ARQUIVO_CONFIG = "~/rede.conf"  # Caminho do arquivo de configuração no equipamento
NOVO_NTP = "10.0.0.50"


def validar_ip(endereco: str) -> bool:
    """Valida se a string recebida é um endereço IPv4 ou IPv6 válido."""
    try:
        ipaddress.ip_address(endereco)
        return True
    except ValueError:
        return False


def atualizar_ntp_seguro(disp: dict, novo_ip: str, caminho_arquivo: str) -> None:
    nome = disp["nome"]
    arquivo_backup = f"{caminho_arquivo}.bak"

    # 1. Validação prévia do IP antes de abrir qualquer conexão
    if not validar_ip(novo_ip):
        raise ValueError(f"Endereço IP inválido fornecido: '{novo_ip}'")

    print(f"\n[{nome}] Iniciando atualização do NTP para {novo_ip}...")
    cliente = conectar(disp)

    try:
        # Garante que o arquivo existe antes de tentar ler/copiar (evita falha em ambiente limpo)
        executar(cliente, f"touch {caminho_arquivo}")

        # (a) Criar cópia de segurança (backup) do arquivo original
        status_bkp, _, erro_bkp = executar(cliente, f"cp -p {caminho_arquivo} {arquivo_backup}")
        if status_bkp != 0:
            raise RuntimeError(f"Falha ao criar backup: {erro_bkp.strip()}")
        print(f"[{nome}] Backup criado em {arquivo_backup}.")

        # Lê o conteúdo atual do arquivo via SSH
        status_cat, conteudo_atual, erro_cat = executar(cliente, f"cat {caminho_arquivo}")
        if status_cat != 0:
            raise RuntimeError(f"Falha ao ler arquivo original: {erro_cat.strip()}")

        # (b) Preparar alteração de forma IDEMPOTENTE
        # Procura qualquer linha começando com 'ntp_server' (com = ou espaço) e substitui
        padrao = re.compile(r"^ntp_server\s*=.*$", re.MULTILINE)
        nova_linha = f"ntp_server = {novo_ip}"

        if padrao.search(conteudo_atual):
            # Substitui a linha existente sem duplicar
            novo_conteudo = padrao.sub(nova_linha, conteudo_atual)
        else:
            # Adiciona a linha ao final caso ainda não exista
            separador = "" if (not conteudo_atual or conteudo_atual.endswith("\n")) else "\n"
            novo_conteudo = f"{conteudo_atual}{separador}{nova_linha}\n"

        # Grava o novo conteúdo no equipamento usando SFTP (mais seguro que echo/sed)
        sftp = cliente.open_sftp()
        try:
            # Resolve o caminho absoluto caso use '~'
            _, caminho_real, _ = executar(cliente, f"eval echo {caminho_arquivo}")
            caminho_real = caminho_real.strip()

            with sftp.file(caminho_real, "w") as f:
                f.write(novo_conteudo)
        finally:
            sftp.close()

        # (c) Verificar se o valor foi realmente gravado no arquivo
        _, conteudo_pos, _ = executar(cliente, f"cat {caminho_arquivo}")
        linhas_encontradas = [
            linha.strip() for linha in conteudo_pos.splitlines()
            if linha.strip().startswith("ntp_server")
        ]

        # Valida se existe exatamente UMA linha e se ela contém o novo IP
        if linhas_encontradas != [nova_linha]:
            raise RuntimeError(
                f"Verificação falhou! Encontrado: {linhas_encontradas}, esperado: ['{nova_linha}']"
            )

        print(f"[{nome}] Sucesso! Configuração verificada: '{nova_linha}'.")

    except Exception as erro:
        print(f"[{nome}] ERRO: {erro}")
        print(f"[{nome}] Executando rollback (restauração do backup)...")

        # (d) Reverter automaticamente em caso de falha
        status_rev, _, erro_rev = executar(cliente, f"mv -f {arquivo_backup} {caminho_arquivo}")
        if status_rev == 0:
            print(f"[{nome}] Rollback concluído com sucesso. Arquivo original restaurado.")
        else:
            print(f"[{nome}] FALHA CRÍTICA no rollback: {erro_rev.strip()}")

    finally:
        cliente.close()


if __name__ == "__main__":
    # Teste de segurança: valida antes de rodar nos dispositivos
    if not validar_ip(NOVO_NTP):
        print(f"Abortado: '{NOVO_NTP}' não é um endereço IP válido.")
    else:
        for dispositivo in DISPOSITIVOS:
            atualizar_ntp_seguro(dispositivo, NOVO_NTP, ARQUIVO_CONFIG)
