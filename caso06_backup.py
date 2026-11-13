import logging
import os
from datetime import datetime
from pathlib import Path
from conexao import conectar, executar

# Lista de dispositivos (ajuste conforme seu ambiente)
DISPOSITIVOS = [
    {"nome": "R1", "host": "127.0.0.1", "usuario": "r1"},
    {"nome": "R2", "host": "127.0.0.1", "usuario": "r2"},
    {"nome": "R3", "host": "127.0.0.1", "usuario": "r3"},
]

ARQUIVO_REMOTO = "dispositivo.cfg"
PASTA_BASE_BACKUPS = Path("backups")
MAX_BACKUPS = 5

# Configuração do arquivo de log (backup.log) e exibição no terminal
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler("backup.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def rotacionar_backups(pasta_dispositivo: Path, limite: int = MAX_BACKUPS) -> None:
    """Mantém apenas os 'limite' arquivos .cfg mais recentes na pasta."""
    # Como o nome começa com AAAA-MM-DD_HHMMSS, a ordenação alfabética já é cronológica
    arquivos = sorted(pasta_dispositivo.glob("*.cfg"))

    if len(arquivos) > limite:
        excedentes = arquivos[:-limite]
        for arquivo_antigo in excedentes:
            arquivo_antigo.unlink()
            logging.info(f"Rotação: backup antigo removido -> {arquivo_antigo}")


def realizar_backup(disp: dict) -> None:
    nome = disp["nome"]
    pasta_destino = PASTA_BASE_BACKUPS / nome
    pasta_destino.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
    arquivo_local = pasta_destino / f"{timestamp}.cfg"

    cliente = None
    sftp = None

    try:
        cliente = conectar(disp)

        # Descobre o diretório home remoto caso o caminho seja relativo
        _, home_remoto, _ = executar(cliente, "pwd")
        caminho_remoto = f"{home_remoto.strip()}/{ARQUIVO_REMOTO}"

        sftp = cliente.open_sftp()
        sftp.get(caminho_remoto, str(arquivo_local))

        logging.info(f"[{nome}] SUCESSO: Backup salvo em '{arquivo_local}'.")

        # Aplica a política de retenção (mantém os 5 mais recentes)
        rotacionar_backups(pasta_destino, MAX_BACKUPS)

    except FileNotFoundError:
        logging.error(
            f"[{nome}] FALHA: O arquivo '{ARQUIVO_REMOTO}' não foi encontrado no equipamento."
        )
    except Exception as erro:
        logging.error(f"[{nome}] FALHA ao realizar backup: {erro}")
    finally:
        if sftp:
            sftp.close()
        if cliente:
            cliente.close()


if __name__ == "__main__":
    logging.info("=== Iniciando rotina automatizada de backup ===")
    for dispositivo in DISPOSITIVOS:
        realizar_backup(dispositivo)
    logging.info("=== Rotina de backup finalizada ===\n")
