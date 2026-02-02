import re

MAX_LOG_LINES = 50


def strip_ansi(text):
    """Rimuove codici ANSI (colori, ecc) da una stringa."""
    ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
    return ansi_escape.sub("", text)


def process_terminal_output(log_buffer, data):
    """
    Processa l'output del terminale gestendo correttamente carriage return (\r).

    Le progress bar (tqdm, etc.) usano \r per sovrascrivere la riga corrente.
    Questa funzione simula quel comportamento nel buffer di log.
    """
    # Se contiene \r, è una progress bar - teniamo solo l'ultimo stato
    if "\r" in data:
        # Prendi solo l'ultima parte dopo l'ultimo \r (lo stato più recente)
        parts = data.split("\r")
        # Filtra parti vuote e prendi l'ultima non vuota
        non_empty_parts = [p for p in parts if p.strip()]

        if non_empty_parts:
            latest = non_empty_parts[-1]

            # Rimuovi l'ultima riga incompleta dal buffer (la vecchia progress bar)
            while log_buffer and not log_buffer[-1].endswith("\n"):
                log_buffer.pop()

            # Aggiungi solo l'ultimo stato
            if latest.endswith("\n"):
                log_buffer.append(latest)
            else:
                log_buffer.append(latest)
    else:
        # Output normale senza \r - aggiungi normalmente
        lines = data.splitlines(keepends=True)
        for line in lines:
            log_buffer.append(line)
