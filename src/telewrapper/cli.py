#!/usr/bin/env python3
import asyncio
import argparse
import configparser
import os
import sys
import socket
import psutil
import uuid
from collections import deque
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Gestione opzionale pynvml (per evitare crash su macchine non-NVIDIA)
try:
    import pynvml

    PYNVML_INSTALLED = True
except ImportError:
    PYNVML_INSTALLED = False

# --- CONFIGURAZIONE E COSTANTI ---
MAX_LOG_LINES = 50
UPDATE_INTERVAL = 3.0


class TeleWrapper:
    def __init__(self, token, chat_id, command, working_dir):
        self.token = token
        self.chat_id = chat_id
        self.command = command
        self.working_dir = working_dir

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

        # Costruzione Log (Escape per sicurezza HTML/Markdown)
        logs = "".join(self.log_buffer).replace("<", "&lt;").replace(">", "&gt;")
        if not logs:
            logs = "Starting..."

        msg = (
            f"🖥 <b>{self.hostname}</b> (PID: {self.pid})\n"
            f"⚙️ <code>{self.command}</code>\n\n"
            f"Status: {status_icon}\n"
            f"Time: {duration}\n"
            f"CPU: {cpu}% | RAM: {mem}%\n"
        )
        if gpu_stats:
            msg += f"<code>{gpu_stats}</code>\n"

        msg += f"\n📜 <b>Recent Log (Last {MAX_LOG_LINES}):</b>\n"
        msg += f"<pre>{logs}</pre>"

        return msg

    def get_keyboard(self):
        """Genera la tastiera inline."""
        pfx = f"{self.session_id}"

        buttons = [
            [
                InlineKeyboardButton(
                    "🔄 Refresh", callback_data=f"refresh:{pfx}"
                )
            ],
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
                [
                    InlineKeyboardButton(
                        "❌ Chiudi Wrapper", callback_data=f"exit:{pfx}"
                    )
                ]
            )
        return InlineKeyboardMarkup(buttons)

    async def run_process(self):
        """Esegue il comando utente e cattura l'output."""
        # Force unbuffered output for Python scripts
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Se siamo su Windows usiamo una shell diversa, ma per Linux/Mac standard è OK
        self.process = await asyncio.create_subprocess_shell(
            self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.working_dir,
            env=env,
        )

        while True:
            line = await self.process.stdout.readline()
            if not line:
                break
            decoded_line = line.decode("utf-8", errors="replace")
            self.log_buffer.append(decoded_line)
            sys.stdout.write(decoded_line)
            sys.stdout.flush()

        self.return_code = await self.process.wait()
        self.is_running = False

    async def telegram_updater(self, app):
        """Task di background per aggiornare il messaggio dashboard."""
        try:
            msg = await app.bot.send_message(
                chat_id=self.chat_id,
                text=self.build_dashboard_text(),
                parse_mode=ParseMode.HTML,
                reply_markup=self.get_keyboard(),
            )
            self.dashboard_message_id = msg.message_id
        except Exception as e:
            print(f"Errore Telegram Init: {e}")
            return

        while True:
            await asyncio.sleep(UPDATE_INTERVAL)
            if self.shutdown_signal:
                break

            try:
                if self.dashboard_message_id:
                    text = self.build_dashboard_text()
                    try:
                        await app.bot.edit_message_text(
                            chat_id=self.chat_id,
                            message_id=self.dashboard_message_id,
                            text=text,
                            parse_mode=ParseMode.HTML,
                            reply_markup=self.get_keyboard(),
                        )
                    except Exception:
                        pass
            except Exception as e:
                pass

            if not self.is_running and self.shutdown_signal:
                break

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

    if args.config and os.path.exists(args.config):
        config = configparser.ConfigParser()
        config.read(args.config)
        if "Telegram" in config:
            if not token:
                token = config["Telegram"].get("token")
            if not chat_id:
                chat_id = config["Telegram"].get("chat_id")

    if not token:
        token = os.environ.get("TELEGRAM_TOKEN")
    if not chat_id:
        chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("Errore: Token e Chat ID sono obbligatori (via CLI, Config o ENV).")
        sys.exit(1)

    if args.test:
        await run_test_mode(token, chat_id)
        return

    if not args.command:
        print("Errore: Devi specificare un comando da eseguire (o usare --test).")
        sys.exit(1)

    print(f"Starting Wrapper for: {args.command}")

    wrapper = TeleWrapper(token, chat_id, args.command, os.getcwd())
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
        except:
            pass


def entry_point():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrotto manualmente.")


if __name__ == "__main__":
    entry_point()
