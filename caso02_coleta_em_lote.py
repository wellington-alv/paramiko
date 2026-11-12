import json
import csv
import conexao

# 1. Ler o inventario.json
try:
    with open('inventario.json', 'r', encoding='utf-8') as arquivo:
        dispositivos = json.load(arquivo)
except FileNotFoundError:
    print("Erro: O arquivo 'inventario.json' não foi encontrado.")
    exit(1)

# Lista para armazenar as linhas do relatório final
relatorio = []

# 2. Iterar por cada dispositivo do inventário
for disp in dispositivos:
    nome = disp.get("nome", "Desconhecido")
    host = disp.get("host", "0.0.0.0")
    print(f"Coletando dados de: {nome} ({host})...")
    
    # Inicializa o dicionário com dados padrão de falha
    dados_dispositivo = {
        "Dispositivo": nome,
        "IP": host,
        "Status": "Falha",
        "whoami": "N/A",
        "hostname": "N/A",
        "uname_r": "N/A",
        "uptime_p": "N/A",
        "Erro": ""
    }
    
    try:
        # Tenta abrir a conexão SSH
        cliente = conexao.conectar(disp)
        
        # Mapeamento dos comandos exigidos pelos requisitos
        comandos = {
            "whoami": "whoami",
            "hostname": "hostname",
            "uname_r": "uname -r",
            "uptime_p": "uptime -p"
        }
        
        # Executa cada comando sequencialmente
        sucesso_total = True
        for chave, cmd in comandos.items():
            codigo, saida, erro = conexao.executar(cliente, cmd)
            if codigo == 0:
                dados_dispositivo[chave] = saida
            else:
                sucesso_total = False
                dados_dispositivo["Erro"] += f"[{cmd} falhou] "
        
        # Se coletou tudo com sucesso, atualiza o status
        if sucesso_total:
            dados_dispositivo["Status"] = "Sucesso"
            
        cliente.close()
        
    except Exception as e:
        # Requisito: Se falhar, registra o erro e CONTINUA com os demais
        print(f"  [X] Falha ao conectar em {nome}: {e}")
        dados_dispositivo["Erro"] = str(e)
    
    # Adiciona o resultado deste dispositivo (seja sucesso ou falha) na lista global
    relatorio.append(dados_dispositivo)

# 3. Gerar o arquivo inventario_coletado.csv
campos = ["Dispositivo", "IP", "Status", "whoami", "hostname", "uname_r", "uptime_p", "Erro"]

with open('inventario_coletado.csv', 'w', newline='', encoding='utf-8') as f_csv:
    escritor = csv.DictWriter(f_csv, fieldnames=campos, delimiter=';')
    escritor.writeheader()
    escritor.writerows(relatorio)

print("\n[✓] Coleta concluída! Arquivo 'inventario_coletado.csv' gerado com sucesso.")
