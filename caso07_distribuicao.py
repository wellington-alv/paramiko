import hashlib
from pathlib import Path
from conexao import conectar, executar

DISPOSITIVOS = [
    {"nome": "R1", "host": "127.0.0.1", "usuario": "r1"},
    {"nome": "R2", "host": "127.0.0.1", "usuario": "r2"},
    {"nome": "R3", "host": "127.0.0.1", "usuario": "r3"},
]

ARQUIVO_LOCAL = Path("coleta.sh")

CONTEUDO_COLETA = """#!/bin/bash
echo "========================================"
echo "Data/Hora : $(date '+%Y-%m-%d %H:%M:%S')"
echo "Hostname  : $(hostname)"
echo "Usuario   : $(whoami)"
echo "Uso Disco :"
df -h / | tail -n 1
echo "========================================"
"""


def garantir_script_local(caminho: Path) -> None:
    """Cria o arquivo coleta.sh localmente com quebras de linha LF (Unix)."""
    if not caminho.exists():
        # newline="\n" evita erro de '\r' caso seja criado no Windows
        with caminho.open("w", encoding="utf-8", newline="\n") as f:
            f.write(CONTEUDO_COLETA)
        print(f"[LOCAL] Arquivo '{caminho}' criado com sucesso.")


def calcular_sha256_local(caminho: Path) -> str:
    """Calcula o hash SHA-256 do arquivo local."""
    sha256 = hashlib.sha256()
    with caminho.open("rb") as f:
        for bloco in iter(lambda: f.read(4096), b""):
            sha256.update(bloco)
    return sha256.hexdigest()


def distribuir_e_executar(disp: dict, arquivo_local: Path, hash_local: str) -> None:
    nome = disp["nome"]
    cliente = None
    sftp = None

    print(f"\n[{nome}] Conectando ao dispositivo...")
    try:
        cliente = conectar(disp)

        # Descobre o diretório home remoto
        _, home_remoto, _ = executar(cliente, "pwd")
        caminho_remoto = f"{home_remoto.strip()}/{arquivo_local.name}"

        # 1. Envia o arquivo via SFTP (put)
        sftp = cliente.open_sftp()
        sftp.put(str(arquivo_local), caminho_remoto)
        print(f"[{nome}] Arquivo enviado via SFTP para '{caminho_remoto}'.")

        # 2. Torna o script executável (chmod +x)
        status_chmod, _, erro_chmod = executar(cliente, f"chmod +x {caminho_remoto}")
        if status_chmod != 0:
            raise RuntimeError(f"Falha ao aplicar chmod +x: {erro_chmod.strip()}")

        # 3. Calcula o hash SHA-256 no equipamento remoto
        status_hash, saida_hash, erro_hash = executar(cliente, f"sha256sum {caminho_remoto}")
        if status_hash != 0:
            raise RuntimeError(f"Falha ao calcular SHA-256 remoto: {erro_hash.strip()}")

        # O comando sha256sum retorna "<hash>  <caminho>", pegamos só a primeira parte
        hash_remoto = saida_hash.strip().split()[0]

        print(f"[{nome}] SHA-256 Local : {hash_local}")
        print(f"[{nome}] SHA-256 Remoto: {hash_remoto}")

        # 4. Compara os hashes antes de executar
        if hash_local != hash_remoto:
            raise ValueError("Integridade comprometida! Os hashes SHA-256 não conferem.")

        print(f"[{nome}] Integridade verificada! Executando script...")

        # 5. Executa o script remotamente
        status_exec, saida_exec, erro_exec = executar(cliente, caminho_remoto)
        if status_exec != 0:
            raise RuntimeError(f"Erro na execução remota: {erro_exec.strip()}")

        print(f"[{nome}] Saída da coleta:\n{saida_exec.strip()}")

    except Exception as erro:
        print(f"[{nome}] ERRO: {erro}")
    finally:
        if sftp:
            sftp.close()
        if cliente:
            cliente.close()


if __name__ == "__main__":
    garantir_script_local(ARQUIVO_LOCAL)
    hash_esperado = calcular_sha256_local(ARQUIVO_LOCAL)

    for dispositivo in DISPOSITIVOS:
        distribuir_e_executar(dispositivo, ARQUIVO_LOCAL, hash_esperado)
