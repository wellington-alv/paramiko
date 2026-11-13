import socket
import time
import paramiko
from conexao import executar

# Inventário de teste cobrindo os 4 cenários exigidos
INVENTARIO = [
    {
        "nome": "R1-SAUDAVEL",
        "host": "127.0.0.1",
        "porta": 22,
        "usuario": "r1",
        "senha": None,  # Usará a chave ~/.ssh/id_redes ou SSH_SENHA padrão
    },
    {
        "nome": "R2-SENHA-ERRADA",
        "host": "127.0.0.1",
        "porta": 22,
        "usuario": "r2",
        "senha": "SenhaTotalmenteErrada@999",
        "forcar_senha": True,  # Ignora chave SSH para provocar erro de autenticação
    },
    {
        "nome": "R3-PORTA-FECHADA",
        "host": "127.0.0.1",
        "porta": 2299,
        "usuario": "r3",
    },
    {
        "nome": "R4-IP-INEXISTENTE",
        "host": "10.255.255.1",
        "porta": 22,
        "usuario": "r1",
    },
]

MAX_TENTATIVAS_TIMEOUT = 3
TIMEOUT_CONEXAO_SEG = 2.0  # Timeout curto para o teste não demorar muito


def conectar_com_timeout(disp: dict) -> paramiko.SSHClient:
    """Abre a conexão SSH respeitando o timeout definido e o cenário de teste."""
    import os

    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    if disp.get("forcar_senha"):
        # Força falha de autenticação sem usar chaves locais ou agente
        cliente.connect(
            hostname=disp["host"],
            port=disp.get("porta", 22),
            username=disp["usuario"],
            password=disp["senha"],
            look_for_keys=False,
            allow_agent=False,
            timeout=TIMEOUT_CONEXAO_SEG,
        )
    else:
        chave_padrao = os.path.expanduser("~/.ssh/id_redes")
        chave = chave_padrao if os.path.exists(chave_padrao) else None
        senha = disp.get("senha") or os.environ.get("SSH_SENHA", "Redes@2026")

        cliente.connect(
            hostname=disp["host"],
            port=disp.get("porta", 22),
            username=disp["usuario"],
            password=senha,
            key_filename=chave,
            timeout=TIMEOUT_CONEXAO_SEG,
        )

    return cliente


def processar_dispositivo_resiliente(disp: dict) -> dict:
    """Tenta conectar, classifica falhas, aplica retry só em timeout e retorna diagnóstico."""
    nome = disp["nome"]
    host_porta = f"{disp['host']}:{disp.get('porta', 22)}"
    print(f"\n[{nome}] Iniciando acesso a {host_porta}...")

    tentativa = 0
    while tentativa < MAX_TENTATIVAS_TIMEOUT:
        tentativa += 1
        cliente = None

        try:
            cliente = conectar_com_timeout(disp)
            _, saida, _ = executar(cliente, "hostname")
            print(f"[{nome}] SUCESSO na tentativa {tentativa}: hostname = '{saida.strip()}'")

            return {
                "nome": nome,
                "alvo": host_porta,
                "status": "SUCESSO",
                "tentativas": tentativa,
                "causa": "Equipamento acessível e autenticado normalmente.",
            }

        # 1. Falha de Autenticação (Permanente -> NUNCA faz retry para não bloquear conta)
        except paramiko.AuthenticationException as erro:
            print(f"[{nome}] FALHA DE AUTENTICAÇÃO (sem retry): {erro}")
            return {
                "nome": nome,
                "alvo": host_porta,
                "status": "ERRO AUTH",
                "tentativas": tentativa,
                "causa": "Credenciais inválidas (senha incorreta/expirada ou chave não autorizada).",
            }

        # 2. Conexão Recusada (Permanente no momento -> Porta fechada ou daemon parado)
        except ConnectionRefusedError as erro:
            print(f"[{nome}] CONEXÃO RECUSADA (sem retry): {erro}")
            return {
                "nome": nome,
                "alvo": host_porta,
                "status": "RECUSADA",
                "tentativas": tentativa,
                "causa": "Porta TCP fechada, serviço SSH parado ou bloqueio ativo (REJECT).",
            }

        # 3. Timeout de Rede (Temporário -> Aplica retry com espera crescente / backoff)
        except (socket.timeout, TimeoutError) as erro:
            espera = 2 ** (tentativa - 1)  # 1s, 2s, 4s...
            print(f"[{nome}] TIMEOUT na tentativa {tentativa}/{MAX_TENTATIVAS_TIMEOUT} ({erro}).")

            if tentativa < MAX_TENTATIVAS_TIMEOUT:
                print(f"[{nome}] Aguardando {espera}s antes de tentar novamente...")
                time.sleep(espera)
            else:
                return {
                    "nome": nome,
                    "alvo": host_porta,
                    "status": "TIMEOUT",
                    "tentativas": tentativa,
                    "causa": "Host desligado, rota inexistente ou firewall descartando pacotes (DROP).",
                }

        # 4. Outras falhas de SSH ou Rede (ex: NoValidConnectionsError, SSHException, OSError)
        except paramiko.ssh_exception.NoValidConnectionsError as erro:
            # O Paramiko costuma encapsular ConnectionRefusedError dentro de NoValidConnectionsError
            print(f"[{nome}] CONEXÃO RECUSADA / INACESSÍVEL (sem retry): {erro}")
            return {
                "nome": nome,
                "alvo": host_porta,
                "status": "RECUSADA",
                "tentativas": tentativa,
                "causa": "Porta fechada ou serviço SSH não está escutando no destino.",
            }

        except (paramiko.SSHException, OSError) as erro:
            print(f"[{nome}] OUTRA FALHA SSH/REDE (sem retry): {erro}")
            return {
                "nome": nome,
                "alvo": host_porta,
                "status": "ERRO SSH",
                "tentativas": tentativa,
                "causa": f"Falha de protocolo SSH ou rede: {erro}",
            }

        finally:
            if cliente:
                cliente.close()


def exibir_relatorio_final(resultados: list[dict]) -> None:
    """Apresenta o relatório consolidado com a causa provável de cada ocorrência."""
    largura = 100
    print("\n" + "=" * largura)
    print(" RELATÓRIO DE RESILIÊNCIA E DIAGNÓSTICO DE FALHAS")
    print("=" * largura)
    print(f"{'DISPOSITIVO':<18} | {'ALVO':<18} | {'STATUS':<10} | {'TENT.':<5} | {'CAUSA PROVÁVEL'}")
    print("-" * largura)

    for r in resultados:
        print(
            f"{r['nome']:<18} | {r['alvo']:<18} | {r['status']:<10} | "
            f"{r['tentativas']:<5} | {r['causa']}"
        )

    print("=" * largura)


if __name__ == "__main__":
    print("=== INICIANDO VARREDURA RESILIENTE DE EQUIPAMENTOS ===")
    relatorio = [processar_dispositivo_resiliente(item) for item in INVENTARIO]
    exibir_relatorio_final(relatorio)
