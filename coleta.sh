#!/bin/bash
echo "========================================"
echo "Data/Hora : $(date '+%Y-%m-%d %H:%M:%S')"
echo "Hostname  : $(hostname)"
echo "Usuario   : $(whoami)"
echo "Uso Disco :"
df -h / | tail -n 1
echo "========================================"
