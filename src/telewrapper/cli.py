#!/usr/bin/env python3
import asyncio
import os
import sys
from collections import deque
from telegram.ext import Application, CallbackQueryHandler
from telegram.constants import ParseMode

from telewrapper.config import load_config
from telewrapper.logs import MAX_LOG_LINES
from telewrapper.system_stats import SystemMonitor
from telewrapper.process import ProcessManager
from telewrapper.bot import TeleWrapperBot


async def run_test_mode(token, chat_id):
    """Esegue un test rapido delle funzionalità del bot."""
    print("🔵 Avvio test funzionalità Telewrapper...")
    try:
        # Inizializza Application
        app = Application.builder().token(token).build()

        # Inizializza SystemMonitor per testare stats
        monitor = SystemMonitor()

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
            cpu, mem, gpu = monitor.get_stats()
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
            monitor.close()

        print("🟢 Test completato con successo!")

    except Exception as e:
        print(f"❌ ERRORE durante il test: {e}")
        sys.exit(1)


async def main():
    command, token, chat_id, update_interval, is_test = load_config()

    if not token or not chat_id:
        print("Errore: Token e Chat ID sono obbligatori (via CLI, Config o ENV).")
        sys.exit(1)

    if is_test:
        await run_test_mode(token, chat_id)
        return

    if not command:
        print("Errore: Devi specificare un comando da eseguire (o usare --test).")
        sys.exit(1)

    print(f"Starting Wrapper for: {command} (update interval: {update_interval}s)")

    # Setup components
    log_buffer = deque(maxlen=MAX_LOG_LINES)
    system_monitor = SystemMonitor()
    process_manager = ProcessManager(command, os.getcwd(), log_buffer)
    bot = TeleWrapperBot(token, chat_id, command, process_manager, system_monitor, update_interval)

    app = Application.builder().token(token).build()
    app.add_handler(CallbackQueryHandler(bot.handle_button))

    async with app:
        await app.start()
        await app.updater.start_polling()
        updater_task = asyncio.create_task(bot.telegram_updater(app))
        
        # Start process
        await process_manager.run()

        # Wait for shutdown signal (from bot or process completion)
        while not bot.shutdown_signal:
            await asyncio.sleep(1)

        await app.updater.stop()
        updater_task.cancel()
        await app.stop()

    system_monitor.close()


def entry_point():
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nInterrotto manualmente.")


if __name__ == "__main__":
    entry_point()
