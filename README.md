# TeleWrapper 🤖

TeleWrapper è un tool CLI avanzato per monitorare l'esecuzione di script e comandi da remoto tramite Telegram. Progettato per task di lunga durata (es. training AI), offre una dashboard in tempo reale con statistiche GPU/CPU e log output.

## Funzionalità Chiave

*   **Live Dashboard**: Un singolo messaggio Telegram "pinned" che si aggiorna automaticamente.
*   **Resource Monitoring**: Monitoraggio Real-time di CPU, RAM e **NVIDIA GPU** (Utilizzo/VRAM).
*   **Decentralized Swarm**: Supporta esecuzioni multiple su macchine diverse usando lo stesso Bot Token senza conflitti.
*   **Smart Download**: Naviga e scarica gli ultimi file generati (es. grafici, log) direttamente dai pulsanti inline.
*   **Zombie Mode**: Al termine dello script, il wrapper rimane attivo per permettere il download dei risultati finché non viene terminato manualmente.

## Installazione

Dalla cartella del progetto:

```bash
pip install .