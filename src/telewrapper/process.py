import asyncio
import os
import sys
import platform
from telewrapper.logs import process_terminal_output

# Rileva sistema operativo
IS_WINDOWS = platform.system() == "Windows"

# Moduli Unix-only (PTY per terminal emulation)
if not IS_WINDOWS:
    import pty
    import select


class ProcessManager:
    def __init__(self, command, working_dir, log_buffer):
        self.command = command
        self.working_dir = working_dir
        self.log_buffer = log_buffer
        self.process = None
        self.is_running = True
        self.return_code = None

    async def run(self):
        """Esegue il comando utente e cattura l'output."""
        if IS_WINDOWS:
            await self._run_process_windows()
        else:
            await self._run_process_unix()

    async def _run_process_windows(self):
        """Implementazione Windows usando subprocess standard con PIPE."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self.process = await asyncio.create_subprocess_shell(
            self.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=self.working_dir,
            env=env,
        )

        async def read_output():
            while True:
                try:
                    # Leggi una riga alla volta
                    line = await self.process.stdout.readline()
                    if not line:
                        break
                    decoded = line.decode("utf-8", errors="replace")
                    process_terminal_output(self.log_buffer, decoded)
                    sys.stdout.write(decoded)
                    sys.stdout.flush()
                except Exception:
                    break

        await read_output()
        self.return_code = await self.process.wait()
        self.is_running = False

    async def _run_process_unix(self):
        """Implementazione Unix/macOS usando PTY per terminal emulation."""
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Usa PTY per forzare line-buffered output (simula un terminale reale)
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

            while True:
                # Usa select per non bloccare
                readable, _, _ = select.select([master_fd], [], [], 0.1)

                if readable:
                    try:
                        data = os.read(master_fd, 4096)
                        if not data:
                            break
                        decoded = data.decode("utf-8", errors="replace")
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

    def terminate(self):
        if self.process and self.is_running:
            try:
                self.process.terminate()
                self.log_buffer.append("\n[WRAPPER] Sent SIGTERM to process...\n")
            except Exception as e:
                self.log_buffer.append(f"\n[WRAPPER] Error killing: {e}\n")
