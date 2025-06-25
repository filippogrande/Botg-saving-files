#!/bin/bash

# Script per installare megatools sul server
# Esegui questo script sul server per installare il tool necessario per Mega

echo "🔧 Installazione di megatools per supporto Mega..."

# Controlla se megatools è già installato
if command -v megadl &> /dev/null; then
    echo "✅ megatools è già installato"
    megadl --version
    exit 0
fi

# Installa megatools
echo "📦 Installazione di megatools..."

# Aggiorna i repository
echo "Aggiornamento repository..."
apt update

# Metodo 1: Tramite apt (Ubuntu/Debian)
if command -v apt &> /dev/null; then
    echo "Provo con apt..."
    apt install -y megatools
    if command -v megadl &> /dev/null; then
        echo "✅ megatools installato con successo via apt"
        megadl --version
        exit 0
    fi
fi

# Metodo 2: Tramite snap (se disponibile)
if command -v snap &> /dev/null; then
    echo "Provo con snap..."
    snap install megatools
    if command -v megadl &> /dev/null; then
        echo "✅ megatools installato con successo via snap"
        megadl --version
        exit 0
    fi
fi

# Metodo 3: Compilazione da sorgente
echo "Provo compilazione da sorgente..."
if command -v git &> /dev/null && command -v make &> /dev/null; then
    # Installa dipendenze per la compilazione
    apt install -y build-essential libglib2.0-dev libssl-dev libcurl4-openssl-dev
    
    # Clone e compila
    cd /tmp
    git clone https://github.com/megous/megatools.git
    cd megatools
    make
    make install
    
    if command -v megadl &> /dev/null; then
        echo "✅ megatools installato con successo da sorgente"
        megadl --version
        exit 0
    fi
fi

# Verifica installazione finale
if command -v megadl &> /dev/null; then
    echo "✅ megatools installato con successo"
    megadl --version
else
    echo "❌ Installazione fallita. Installazione manuale necessaria:"
    echo "1. Su Ubuntu/Debian: sudo apt install megatools"
    echo "2. Su CentOS/RHEL: sudo yum install megatools"
    echo "3. Oppure compila da: https://github.com/megous/megatools"
    echo ""
    echo "Come alternativa, installa gdown per file singoli:"
    echo "pip install gdown"
fi
