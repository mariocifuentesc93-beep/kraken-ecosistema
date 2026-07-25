from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess


def _normalized(path):
    return str(Path(path).resolve()).replace("/", "\\").casefold()


class SubprocessBackend:
    def running_executables(self):
        return []

    def start(self, executable, arguments):
        process = subprocess.Popen(
            [executable, *arguments],
            cwd=str(Path(executable).parent),
            shell=False,
        )
        return process.pid


class MT5TerminalLauncher:
    def __init__(self, process_backend=None, executor=None):
        self.process_backend = process_backend or SubprocessBackend()
        self.executor = executor or ThreadPoolExecutor(
            max_workers=2, thread_name_prefix="mt5-launch"
        )

    def build_arguments(self, terminal):
        return ["/portable"] if terminal.portable else []

    def is_running(self, executable_path):
        target = _normalized(executable_path)
        return any(
            _normalized(path) == target
            for path in self.process_backend.running_executables()
        )

    def launch(self, terminal):
        executable = Path(terminal.executable_path)
        if not executable.is_file():
            raise FileNotFoundError(f"No existe el terminal: {executable}")
        if self.is_running(executable):
            raise RuntimeError("Esta instalación MT5 ya está ejecutándose.")
        return self.process_backend.start(
            str(executable), self.build_arguments(terminal)
        )

    def launch_async(self, terminal):
        return self.executor.submit(self.launch, terminal)
