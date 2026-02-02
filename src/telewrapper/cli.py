#!/usr/bin/env python3
import asyncio
import argparse
import configparser
import os
import sys
import yaml
import socket
import psutil
import uuid
import warnings
import html
import re
import pty
import select
from collections import deque
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.error import BadRequest, RetryAfter, NetworkError, TimedOut

# Gestione opzionale pynvml (per evitare crash su macchine non-NVIDIA)
try:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=FutureWarning)
        import pynvml

    PYNVML_INSTALLED = True
except ImportError:
    PYNVML_INSTALLED = False

# --- CONFIGURAZIONE E COSTANTI ---
MAX_LOG_LINES = 50
DEFAULT_UPDATE_INTERVAL = 5.0


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


class TeleWrapper:
    def __init__(self, token, chat_id, command, working_dir, update_interval=None):
        self.token = token
        self.chat_id = chat_id
        self.command = command
        self.working_dir = working_dir
        self.update_interval = update_interval or DEFAULT_UPDATE_INTERVAL

        # Identificativo Univoco Sessione (Hostname + PID)
        self.hostname = socket.gethostname()
        self.pid = os.getpid()
        # Usa un UUID breve per evitare problemi con caratteri speciali o lunghezza
        self.session_id = str(uuid.uuid4())[:8]
        self.shutdown_signal = False

        # Stato
        self.process = None
        self.log_buffer = deque(maxlen=MAX_LOG_LINES)
        self.is_running = True
        self.return_code = None
        self.start_time = datetime.now()

        # Telegram Message ID
        self.dashboard_message_id = None
        self.last_message_text = None

        # Inizializzazione GPU
        self.gpu_available = False
        if PYNVML_INSTALLED:
            try:
                pynvml.nvmlInit()
                self.gpu_available = True
            except Exception:
                pass

    def get_system_stats(self):
        """Raccoglie info su CPU, RAM e GPU."""
        cpu = psutil.cpu_percent()
        mem = psutil.virtual_memory().percent

        gpu_info = ""
        if self.gpu_available:
            try:
                device_count = pynvml.nvmlDeviceGetCount()
                for i in range(device_count):
                    handle = pynvml.nvmlDeviceGetHandleByIndex(i)
                    util = pynvml.nvmlDeviceGetUtilizationRates(handle).gpu
                    mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
                    used_mem_gb = mem_info.used / 1024**3
                    total_mem_gb = mem_info.total / 1024**3
                    vram_percent = (mem_info.used / mem_info.total) * 100
                    gpu_info += f"GPU {i}: {util}% | VRAM: {used_mem_gb:.1f}/{total_mem_gb:.1f}GB ({vram_percent:.0f}%)\n"
            except Exception:
                gpu_info = "GPU Err"

        return cpu, mem, gpu_info.strip()

    def build_dashboard_text(self):
        """Costruisce il messaggio di stato."""
        cpu, mem, gpu_stats = self.get_system_stats()
        duration = str(datetime.now() - self.start_time).split(".")[0]

        status_icon = (
            "🟢 Running"
            if self.is_running
            else (
                f"✅ Done (Exit: {self.return_code})"
                if self.return_code == 0
                else f"❌ Error (Exit: {self.return_code})"
            )
        )

        # Costruzione Log (Clean ANSI & Escape HTML)
        raw_logs = "".join(self.log_buffer)
        clean_logs = strip_ansi(raw_logs)
        logs = html.escape(clean_logs)

        if not logs:
            logs = "Starting..."

        # Escape other fields per sicurezza HTML
        safe_hostname = html.escape(self.hostname)
        safe_command = html.escape(self.command)
        safe_gpu_stats = html.escape(gpu_stats) if gpu_stats else ""

        header = (
            f"🖥 <b>{safe_hostname}</b> (PID: {self.pid})\n"
            f"⚙️ <code>{safe_command}</code>\n\n"
            f"Status: {status_icon}\n"
            f"Time: {duration}\n"
            f"CPU: {cpu}% | RAM: {mem}%\n"
        )
        if safe_gpu_stats:
            header += f"<code>{safe_gpu_stats}</code>\n"

        header += f"\n📜 <b>Recent Log (Last {MAX_LOG_LINES}):</b>\n"

        # Calcolo spazio disponibile (Telegram limit 4096)
        max_len = 4096
        overhead = len(header) + len("<pre></pre>") + 20
        available_chars = max_len - overhead

        if len(logs) > available_chars:
            trunc_msg = "\n...[truncated]...\n"
            keep_len = available_chars - len(trunc_msg)
            if keep_len > 0:
                logs = trunc_msg + logs[-keep_len:]
            else:
                logs = trunc_msg

        msg = f"{header}<pre>{logs}</pre>"

        return msg

    def get_keyboard(self):
        """Genera la tastiera inline."""
        pfx = f"{self.session_id}"

        buttons = [
            [InlineKeyboardButton("🔄 Refresh", callback_data=f"refresh:{pfx}")],
        ]
        if self.is_running:
            buttons.append(
                [
                    InlineKeyboardButton(
                        "🛑 Termina Processo", callback_data=f"kill:{pfx}"
                    )
                ]
            )
        else:
            buttons.append(
                [InlineKeyboardButton("❌ Chiudi Wrapper", callback_data=f"exit:{pfx}")]
            )
        return InlineKeyboardMarkup(buttons)

    async def run_process(self):
        """Esegue il comando utente e cattura l'output usando PTY per line-buffered output."""
        # Force unbuffered output for Python scripts
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Usa PTY per forzare line-buffered output (simula un terminale reale)
        # Questo risolve il problema dei log non aggiornanti in screen/background
        master_fd, slave_fd = pty.openpty()

        try:
            self.process = await asyncio.create_subprocess_shell(
                self.command,
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=self.working_dir,
                env=env,
            )

            # Chiudi il lato slave nel processo padre
            os.close(slave_fd)

            # Leggi l'output dal master fd in modo non-bloccante
            loop = asyncio.get_event_loop()

            while True:
                # Usa select per non bloccare
                readable, _, _ = select.select([master_fd], [], [], 0.1)

                if readable:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        decoded = data.decode("utf-8", errors="replace")
                        # Usa la funzione che gestisce correttamente \r per le progress bar
                        process_terminal_output(self.log_buffer, decoded)
                        sys.stdout.write(decoded)
                        sys.stdout.flush()
                    except OSError:
                        break

                # Controlla se il processo è terminato
                if self.process.returncode is not None:
                    # Leggi eventuale output rimanente
                    try:
                        while True:
                            readable, _, _ = select.select([master_fd], [], [], 0.1)
                            if not readable:
                                break
                            data = os.read(master_fd, 4096)
                            if not data:
                                break
                            decoded = data.decode("utf-8", errors="replace")
                            process_terminal_output(self.log_buffer, decoded)
                            sys.stdout.write(decoded)
                            sys.stdout.flush()
                    except OSError:
                        pass
                    break

                # Yield per permettere ad altri task di eseguire
                await asyncio.sleep(0.01)

        finally:
            try:
                os.close(master_fd)
            except OSError:
                pass

        self.return_code = await self.process.wait()
        self.is_running = False

    async def telegram_updater(self, app):
        """Task di background per aggiornare il messaggio dashboard."""
        try:
            initial_text = self.build_dashboard_text()
            msg = await app.bot.send_message(
                chat_id=self.chat_id,
                text=initial_text,
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard(),
            )
            self.dashboard_message_id = msg.message_id
            self.last_message_text = initial_text
        except Exception as e:
            print(f"Errore Telegram Init: {e}")
            return

        while True:
            await asyncio.sleep(self.update_interval)
            if self.shutdown_signal:
                break

            try:
                if self.dashboard_message_id:
                    text = self.build_dashboard_text()

                    # Evita chiamate API inutili se il testo non è cambiato
                    if text == self.last_message_text:
                        continue

                    try:
                        await app.bot.edit_message_text(
                            chat_id=self.chat_id,
                            message_id=self.dashboard_message_id,
                            text=text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=self.get_keyboard(),
                        )
                        self.last_message_text = text
                    except BadRequest as e:
                        if "Message is not modified" in str(e):
                            # Ignora errore se il messaggio è identico (caso limite)
                            pass
                        else:
                            print(f"Telegram BadRequest: {e}")
                    except RetryAfter as e:
                        print(f"Telegram FloodLimit: sleeping {e.retry_after}s")
                        await asyncio.sleep(e.retry_after)
                    except (NetworkError, TimedOut):
                        # Problemi di rete temporanei, riprova al prossimo ciclo
                        pass
                    except Exception as e:
                        print(f"Telegram Update Error: {e}")

            except Exception as e:
                print(f"Critical Loop Error: {e}")

    async def handle_button(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        print(f"DEBUG: Button clicked: {query.data}")

        try:
            data = query.data.split(":")
            action = data[0]
            target_session = data[1]

            if target_session != self.session_id:
                print(f"DEBUG: Session mismatch: {target_session} != {self.session_id}")
                await query.answer("Sessione scaduta o non valida", show_alert=True)
                return

            await query.answer()

            if action == "refresh":
                # Il refresh avviene automaticamente, ma possiamo forzare un update immediato se necessario
                pass

            elif action == "kill":
                if self.process and self.is_running:
                    try:
                        self.process.terminate()
                        self.log_buffer.append(
                            "\n[WRAPPER] Sent SIGTERM to process...\n"
                        )
                    except Exception as e:
                        self.log_buffer.append(f"\n[WRAPPER] Error killing: {e}\n")

            elif action == "exit":
                self.shutdown_signal = True
                # Ferma l'updater impostando il segnale, poi aggiorna il messaggio finale
                await query.edit_message_text(
                    f"🛑 Wrapper su {self.hostname} terminato."
                )
        except Exception as e:
            print(f"ERROR in handle_button: {e}")
            self.log_buffer.append(f"[Wrapper Error] Button handler: {e}\n")


async def run_test_mode(token, chat_id):
    """Esegue un test rapido delle funzionalità del bot."""
    print("🔵 Avvio test funzionalità Telewrapper...")
    try:
        # Inizializza Application
        app = Application.builder().token(token).build()

        # Inizializza Wrapper fittizio per testare stats
        wrapper = TeleWrapper(token, chat_id, "echo 'Test Mode'", os.getcwd())

        async with app:
            await app.start()

            # 1. Test Invio Messaggio
            print("📨 Invio messaggio di test a Telegram...")
            msg_text = (
                "🔔 <b>Telewrapper Test</b>\n\n"
                "Se leggi questo messaggio, il bot funziona correttamente!\n"
                "Sto verificando le statistiche di sistema..."
            )
            await app.bot.send_message(
                chat_id=chat_id, text=msg_text, parse_mode=ParseMode.HTML
            )
            print("✅ Messaggio inviato.")

            # 2. Test Statistiche
            print("📊 Verifica statistiche di sistema...")
            cpu, mem, gpu = wrapper.get_system_stats()
            stats_msg = (
                f"✅ <b>Test Completato</b>\n\n"
                f"CPU: {cpu}%\n"
                f"RAM: {mem}%\n"
                f"GPU: {gpu if gpu else 'Non rilevata/Disponibile'}"
            )
            print(f"   CPU: {cpu}%, RAM: {mem}%, GPU: {gpu}")

            await app.bot.send_message(
                chat_id=chat_id, text=stats_msg, parse_mode=ParseMode.HTML
            )
            print("✅ Statistiche inviate.")

            await app.stop()

        print("🟢 Test completato con successo!")

    except Exception as e:
        print(f"❌ ERRORE durante il test: {e}")
        sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(description="Telegram Command Wrapper")
    parser.add_argument(
        "command", nargs="?", help="Il comando da eseguire (tra virgolette)"
    )
    parser.add_argument("--token", help="Bot Token Telegram")
    parser.add_argument("--chat_id", help="Chat ID Telegram")
    parser.add_argument("--config", help="Path al file di config")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Esegui un test di connessione e funzionalità",
    )

    args = parser.parse_args()

    token = args.token
    chat_id = args.chat_id
    update_interval = None

    # Parsing config file (supporta YAML e INI)
    if args.config and os.path.exists(args.config):
        config_path = args.config

        if config_path.endswith((".yaml", ".yml")):
            # YAML config
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
            if config:
                telegram_config = config.get("telegram", {})
                if not token:
                    token = telegram_config.get("token")
                if not chat_id:
                    chat_id = telegram_config.get("chat_id")
                # Leggi update_interval dalla config
                settings = config.get("settings", {})
                update_interval = settings.get("update_interval", update_interval)
        else:
            # INI config (retrocompatibilità)
            ini_config = configparser.ConfigParser()
            ini_config.read(config_path)
            if "Telegram" in ini_config:
                if not token:
                    token = ini_config["Telegram"].get("token")
                if not chat_id:
                    chat_id = ini_config["Telegram"].get("chat_id")
            if "Settings" in ini_config:
                update_interval = ini_config["Settings"].getfloat(
                    "update_interval", fallback=update_interval
                )

    if not token:
        token = os.environ.get("TELEGRAM_TOKEN")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID") or os.environ.get("CHAT_ID")

    if not token or not chat_id:
        print("Errore: Token e Chat ID sono obbligatori (via CLI, Config o ENV).")
        sys.exit(1)

    if args.test:
        await run_test_mode(token, chat_id)
        return

    if not args.command:
        print("Errore: Devi specificare un comando da eseguire (o usare --test).")
        sys.exit(1)

    if update_interval:
        print(
            f"Starting Wrapper for: {args.command} (update interval: {update_interval}s)"
        )
    else:
        print(f"Starting Wrapper for: {args.command}")

    wrapper = TeleWrapper(token, chat_id, args.command, os.getcwd(), update_interval)
    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(wrapper.handle_button))

    async with app:
        await app.start()
        await app.updater.start_polling()
        updater_task = asyncio.create_task(wrapper.telegram_updater(app))
        await wrapper.run_process()

        while not wrapper.shutdown_signal:
            await asyncio.sleep(1)

        await app.updater.stop()
        updater_task.cancel()
        await app.stop()

    if wrapper.gpu_available:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass


def entry_point():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrotto manualmente.")


if __name__ == "__main__":
    entry_point()
