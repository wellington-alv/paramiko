for u in r1 r2 r3 bastion; do
  sudo useradd -m -s /bin/bash $u
  echo "$u:Redes@2026" | sudo chpasswd
done

# Arquivo de configuração simulado de cada "equipamento"
for u in r1 r2 r3; do
  printf "hostname=$u\nntp_server=10.0.0.1\nsnmp_community=public\nlogging_level=info\n" \
    | sudo tee /home/$u/dispositivo.cfg > /dev/null
  sudo chown $u:$u /home/$u/dispositivo.cfg
done