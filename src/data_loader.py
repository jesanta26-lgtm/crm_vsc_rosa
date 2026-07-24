from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = (
    PROJECT_ROOT
    / "data"
    / "raw"
    / "Casos resueltos VSC 22-07-2026 13-16-49.xlsx"
)


def load_cases_data(file_path: Path | str = DATA_PATH) -> pd.DataFrame:
    """
    Carga la base de casos desde un archivo Excel.

    Parameters
    ----------
    file_path:
        Ruta del archivo Excel.

    Returns
    -------
    pd.DataFrame
        DataFrame con los casos registrados.
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo: {file_path}"
        )

    try:
        return pd.read_excel(
            file_path,
            engine="openpyxl",
        )

    except Exception as error:
        raise RuntimeError(
            f"No fue posible cargar el archivo: {error}"
        ) from error
