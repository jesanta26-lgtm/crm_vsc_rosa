from typing import BinaryIO

import pandas as pd


def load_cases_data(
    source: BinaryIO,
) -> pd.DataFrame:
    """
    Carga la base de casos desde un archivo Excel cargado
    mediante Streamlit.

    Parameters
    ----------
    source:
        Archivo cargado por el usuario desde st.file_uploader.

    Returns
    -------
    pd.DataFrame
        DataFrame con la información de los casos.
    """
    if source is None:
        raise ValueError(
            "No se recibió ningún archivo para procesar."
        )

    try:
        return pd.read_excel(
            source,
            engine="openpyxl",
        )

    except ValueError as error:
        raise ValueError(
            "El archivo no tiene un formato Excel válido."
        ) from error

    except Exception as error:
        raise RuntimeError(
            f"No fue posible cargar el archivo: {error}"
        ) from error
