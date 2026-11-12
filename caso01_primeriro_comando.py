import json
import conexao

# Lendo o arquivo JSON
with open('inventario.json', 'r', encoding='utf-8') as arquivo:
    dados = json.load(arquivo)

# Conectar-se ao equipamento R1 do inventário
cliente = conexao.conectar(dados[0])

# Executar os comandos solicitados (whoami, hostname, uptime -p)
comandos = ["whoami", "hostname", "uptime -p"]

for cmd in comandos:
    print(f"\n--- Executando: {cmd} ---")
    codigo, saida, erro = conexao.executar(cliente, cmd)
    
    
    # Exibir, para cada comando, o código de saída, a saída padrão e a saída de erro
    print(f"Código: {codigo}")
    print(f"Saída: {saida}")
    print(f"Erro: {erro}")

# Fechar a conexão ao terminar
cliente.close()
