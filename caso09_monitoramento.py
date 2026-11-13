from datetime import datetime
from conexao import conectar, executar

DISPOSITIVOS = [
    {"nome": "R1", "host": "127.0.0.1", "usuario": "r1"},
    {"nome": "R2", "host": "127.0.0.1", "usuario": "r2"},
    {"nome": "R3", "host": "127.0.0.1", "usuario": "r3"},
]

# Limiares de alerta do NOC
LIMIAR_DISCO_PCT = 80
LIMIAR_CARGA_1MIN = 2.0


def verificar_saude(disp: dict) -> dict:
    """Coleta métricas de disco, carga e serviço SSH, retornando o status classificado."""
    nome = disp["nome"]
    resultado = {
        "nome": nome,
        "status": "OK",
        "disco": "N/A",
        "carga": "N/A",
        "sshd": "N/A",
        "detalhes": "Operando dentro dos parâmetros normais.",
    }

    cliente = None
    try:
        cliente = conectar(disp)

        # 1. Ocupação do disco raiz (/) -> retorna apenas o número percentual (ex: 42)
        st_disco, out_disco, err_disco = executar(
            cliente, "df -P / | awk 'NR==2 {gsub(\"%\", \"\", $5); print $5}'"
        )
        if st_disco != 0 or not out_disco.strip().isdigit():
            raise RuntimeError(f"Falha ao ler disco: {err_disco.strip()}")
        uso_disco = int(out_disco.strip())
        resultado["disco"] = f"{uso_disco}%"

        # 2. Carga média de 1 minuto (/proc/loadavg) -> primeiro campo
        st_carga, out_carga, err_carga = executar(cliente, "awk '{print $1}' /proc/loadavg")
        if st_carga != 0:
            raise RuntimeError(f"Falha ao ler carga média: {err_carga.strip()}")
        carga_1min = float(out_carga.strip().replace(",", "."))
        resultado["carga"] = f"{carga_1min:.2f}"

        # 3. Verificação se o processo/serviço sshd está em execução
        st_ssh, _, _ = executar(cliente, "pgrep -x sshd >/dev/null && echo ATIVO || echo PARADO")
        # Verifica pela saída textual para garantir compatibilidade
        _, out_ssh_txt, _ = executar(
            cliente, "pgrep -x sshd >/dev/null 2>&1 && echo ATIVO || echo PARADO"
        )
        sshd_ativo = out_ssh_txt.strip() == "ATIVO"
        resultado["sshd"] = "ATIVO" if sshd_ativo else "PARADO"

        # 4. Avaliação dos limiares e classificação
        alertas = []
        if not sshd_ativo:
            alertas.append("Serviço sshd fora de execução")
        if uso_disco > LIMIAR_DISCO_PCT:
            alertas.append(f"Disco em {uso_disco}% (limite {LIMIAR_DISCO_PCT}%)")
        if carga_1min > LIMIAR_CARGA_1MIN:
            alertas.append(f"Carga 1m em {carga_1min:.2f} (limite {LIMIAR_CARGA_1MIN:.1f})")

        if alertas:
            resultado["status"] = "ALERTA"
            resultado["detalhes"] = "; ".join(alertas)

    except Exception as erro:
        resultado["status"] = "FALHA"
        resultado["detalhes"] = f"Erro de conexão/coleta: {erro}"
    finally:
        if cliente:
            cliente.close()

    return resultado


def exibir_painel_noc(resultados: list[dict]) -> None:
    """Imprime o painel formatado com o resumo da saúde da rede."""
    agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    largura = 86

    print("=" * largura)
    print(f" PAINEL DE MONITORAMENTO DE SAÚDE - NOC | {agora}")
    print("=" * largura)
    print(f"{'EQUIP.':<8} | {'STATUS':<8} | {'DISCO (/)':<10} | {'CARGA (1m)':<11} | {'SSHD':<8} | {'DIAGNÓSTICO'}")
    print("-" * largura)

    contadores = {"OK": 0, "ALERTA": 0, "FALHA": 0}

    for r in resultados:
        contadores[r["status"]] += 1
        print(
            f"{r['nome']:<8} | {r['status']:<8} | {r['disco']:<10} | "
            f"{r['carga']:<11} | {r['sshd']:<8} | {r['detalhes']}"
        )

    print("-" * largura)
    print(
        f" RESUMO: {len(resultados)} equipamentos verificados -> "
        f"OK: {contadores['OK']} | ALERTA: {contadores['ALERTA']} | FALHA: {contadores['FALHA']}"
    )
    print("=" * largura)


if __name__ == "__main__":
    relatorio = [verificar_saude(disp) for disp in DISPOSITIVOS]
    exibir_painel_noc(relatorio)
