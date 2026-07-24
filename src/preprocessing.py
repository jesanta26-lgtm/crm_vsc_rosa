"""
Funciones para limpiar y preparar la información de casos del CRM.
"""

from typing import Any

import pandas as pd


DATE_COLUMNS = [
    "Fecha de apertura",
    "Fecha asigno caso",
    "Fecha atendió Facturación",
    "Fecha de resolución",
]

REQUIRED_DATE_COLUMNS = [
    "Fecha de apertura",
    "Fecha atendió Facturación",
    "Fecha de resolución",
]


def validate_required_columns(
    data: pd.DataFrame,
    required_columns: list[str],
) -> None:
    """
    Verifica que existan las columnas obligatorias.
    """

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "Faltan columnas obligatorias en el archivo: "
            + ", ".join(missing_columns)
        )


def clean_text_columns(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Limpia espacios y valores vacíos en columnas de texto.
    """

    text_columns = data.select_dtypes(
        include=["object", "string"]
    ).columns

    for column in text_columns:
        data[column] = (
            data[column]
            .astype("string")
            .str.strip()
            .replace(
                {
                    "": pd.NA,
                    "nan": pd.NA,
                    "None": pd.NA,
                    "NaN": pd.NA,
                }
            )
        )

    return data


def identify_discard_reason(
    row: pd.Series,
    required_dates: list[str],
) -> str:
    """
    Identifica la causa del descarte de un registro.
    """

    reasons = []

    missing_dates = [
        column
        for column in required_dates
        if pd.isna(row[column])
    ]

    if missing_dates:
        reasons.append(
            "Fecha faltante o inválida: "
            + ", ".join(missing_dates)
        )

    opening_date = row.get("Fecha de apertura")
    billing_date = row.get(
        "Fecha atendió Facturación"
    )
    resolution_date = row.get(
        "Fecha de resolución"
    )

    if (
        pd.notna(opening_date)
        and pd.notna(billing_date)
        and billing_date < opening_date
    ):
        reasons.append(
            "Fecha de atención en Facturación anterior "
            "a la fecha de apertura"
        )

    if (
        pd.notna(billing_date)
        and pd.notna(resolution_date)
        and resolution_date < billing_date
    ):
        reasons.append(
            "Fecha de resolución anterior a la fecha "
            "de atención en Facturación"
        )

    if (
        pd.notna(opening_date)
        and pd.notna(resolution_date)
        and resolution_date < opening_date
    ):
        reasons.append(
            "Fecha de resolución anterior "
            "a la fecha de apertura"
        )

    if not reasons:
        return "Sin motivo identificado"

    return " | ".join(reasons)


def create_sla_range(
    time_values: pd.Series,
) -> pd.Series:
    """
    Clasifica el tiempo en VSC en rangos excluyentes.
    """

    return pd.cut(
        time_values,
        bins=[
            float("-inf"),
            0.5,
            1.0,
            float("inf"),
        ],
        labels=[
            "Hasta 30 min",
            "31 a 60 min",
            "Más de 60 min",
        ],
        include_lowest=True,
        right=True,
    )


def prepare_cases_data(
    dataframe: pd.DataFrame,
) -> tuple[
    pd.DataFrame,
    dict[str, Any],
    pd.DataFrame,
]:
    """
    Limpia y prepara la base de casos.

    La columna Semana contiene el número ISO de semana.
    """

    if dataframe is None:
        raise ValueError(
            "No se recibió información para procesar."
        )

    if dataframe.empty:
        empty_stats = {
            "registros_iniciales": 0,
            "registros_eliminados": 0,
            "registros_finales": 0,
            "porcentaje_eliminado": 0.0,
        }

        return (
            dataframe.copy(),
            empty_stats,
            dataframe.copy(),
        )

    data = dataframe.copy()

    data.columns = (
        data.columns
        .astype(str)
        .str.strip()
    )

    validate_required_columns(
        data,
        REQUIRED_DATE_COLUMNS,
    )

    data = clean_text_columns(data)

    for column in DATE_COLUMNS:
        if column in data.columns:
            data[column] = pd.to_datetime(
                data[column],
                errors="coerce",
                dayfirst=True,
            )

    initial_rows = len(data)

    missing_date_mask = (
        data[REQUIRED_DATE_COLUMNS]
        .isna()
        .any(axis=1)
    )

    invalid_billing_order_mask = (
        data["Fecha de apertura"].notna()
        & data[
            "Fecha atendió Facturación"
        ].notna()
        & (
            data["Fecha atendió Facturación"]
            < data["Fecha de apertura"]
        )
    )

    invalid_resolution_order_mask = (
        data[
            "Fecha atendió Facturación"
        ].notna()
        & data["Fecha de resolución"].notna()
        & (
            data["Fecha de resolución"]
            < data["Fecha atendió Facturación"]
        )
    )

    invalid_total_order_mask = (
        data["Fecha de apertura"].notna()
        & data["Fecha de resolución"].notna()
        & (
            data["Fecha de resolución"]
            < data["Fecha de apertura"]
        )
    )

    discarded_mask = (
        missing_date_mask
        | invalid_billing_order_mask
        | invalid_resolution_order_mask
        | invalid_total_order_mask
    )

    discarded_data = data.loc[
        discarded_mask
    ].copy()

    if not discarded_data.empty:
        discarded_data[
            "Motivo del descarte"
        ] = discarded_data.apply(
            identify_discard_reason,
            axis=1,
            required_dates=REQUIRED_DATE_COLUMNS,
        )
    else:
        discarded_data[
            "Motivo del descarte"
        ] = pd.Series(dtype="string")

    clean_data = data.loc[
        ~discarded_mask
    ].copy()

    removed_rows = len(discarded_data)
    final_rows = len(clean_data)

    cleaning_stats = {
        "registros_iniciales": initial_rows,
        "registros_eliminados": removed_rows,
        "registros_finales": final_rows,
        "porcentaje_eliminado": (
            removed_rows / initial_rows * 100
            if initial_rows > 0
            else 0.0
        ),
    }

    clean_data[
        "Tiempo en Facturación (Hrs)"
    ] = (
        (
            clean_data[
                "Fecha atendió Facturación"
            ]
            - clean_data["Fecha de apertura"]
        )
        .dt.total_seconds()
        .div(3600)
    )

    clean_data[
        "Tiempo en VSC (Hrs)"
    ] = (
        (
            clean_data["Fecha de resolución"]
            - clean_data[
                "Fecha atendió Facturación"
            ]
        )
        .dt.total_seconds()
        .div(3600)
    )

    clean_data[
        "Tiempo total caso (Hrs)"
    ] = (
        (
            clean_data["Fecha de resolución"]
            - clean_data["Fecha de apertura"]
        )
        .dt.total_seconds()
        .div(3600)
    )

    clean_data["Fecha"] = (
        clean_data["Fecha de apertura"]
        .dt.normalize()
    )

    iso_calendar = (
        clean_data["Fecha de apertura"]
        .dt.isocalendar()
    )

    # Año ISO al que pertenece la semana.
    clean_data["Año"] = (
        iso_calendar.year.astype(int)
    )

    # Número ISO de semana: 1 a 52 o 53.
    clean_data["Semana"] = (
        iso_calendar.week.astype(int)
    )

    clean_data["Mes"] = (
        clean_data["Fecha de apertura"]
        .dt.to_period("M")
        .astype(str)
    )

    clean_data["Día de la semana"] = (
        clean_data["Fecha de apertura"]
        .dt.day_name()
    )

    clean_data["Rango SLA"] = create_sla_range(
        clean_data["Tiempo en VSC (Hrs)"]
    )

    clean_data = clean_data.reset_index(
        drop=True
    )

    discarded_data = discarded_data.reset_index(
        drop=True
    )

    return (
        clean_data,
        cleaning_stats,
        discarded_data,
    )
