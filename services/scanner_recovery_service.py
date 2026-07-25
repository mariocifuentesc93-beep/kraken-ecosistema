from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ScannerRecoveryPlan:
    executable_path: str
    current_data_path: str
    original_data_path: str
    strategy: str
    actions: tuple[str, ...]
    warnings: tuple[str, ...]
    executable_exists: bool
    original_exists: bool
    inspector_source_exists: bool
    inspector_binary_exists: bool


class ScannerRecoveryService:
    """Produces a non-destructive recovery plan; it never copies files."""

    def inspect(self, executable_path, current_data_path, original_data_path):
        executable = Path(executable_path)
        current = Path(current_data_path)
        original = Path(original_data_path)
        indicator = original / "MQL5" / "Indicators" / "KrakenBMSPInspector"
        warnings = []
        if not executable.is_file():
            warnings.append("No se encontró terminal64.exe.")
        if not original.is_dir():
            warnings.append("La carpeta de datos original no existe.")
        if current.resolve() != original.resolve():
            warnings.append(
                "La instalación está asociada a una carpeta de datos distinta."
            )
        return ScannerRecoveryPlan(
            executable_path=str(executable),
            current_data_path=str(current),
            original_data_path=str(original),
            strategy="MANAGED_PORTABLE_COPY",
            actions=(
                "Cerrar la instancia Scanner.",
                "Crear respaldo verificable de la carpeta original.",
                "Crear una copia administrada fuera de Program Files.",
                "Copiar terminal e historial MQL5 preservando el original.",
                "Validar hashes de KrakenBMSPInspector.mq5 y .ex5.",
                "Iniciar la copia administrada con /portable.",
                "Confirmar cuenta autorizada, gráficos y salida CSV.",
            ),
            warnings=tuple(warnings),
            executable_exists=executable.is_file(),
            original_exists=original.is_dir(),
            inspector_source_exists=indicator.with_suffix(".mq5").is_file(),
            inspector_binary_exists=indicator.with_suffix(".ex5").is_file(),
        )
