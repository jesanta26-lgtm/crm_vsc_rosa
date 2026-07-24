import pandas as pd


DATE_COLUMNS = [
    "Fecha de apertura",
    "Fecha asigno caso",
    "Fecha atendió Facturación",
    "Fecha de resolución",
]

WEEKDAY_ORDER = [
    "Lunes",
    "Martes",
    "Miércoles",
    "Jueves",
    "Viernes",
    "Sábado",
    "Domingo",
]

WEEKDAY_TRANSLATION = {
    "Monday": "Lunes",
    "Tuesday": "Martes",
    "Wednesday": "Miércoles",
    "Thursday": "Jueves",
    "Friday": "Viernes",
    "Saturday": "Sábado",
    "Sunday": "Domingo",
}


def prepare_cases_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia los datos y genera las variables necesarias para el análisis.
    """
    data = df.copy()

    for column in DATE_COLUMNS:
        if column in data.columns:
            data[column] = pd.to_datetime(
                data[column],
                errors="coerce",
            )

    required_dates = [
        "Fecha de apertura",
        "Fecha atendió Facturación",
        "Fecha de resolución",
    ]

    data = data.dropna(
        subset=required_dates
    ).copy()

    data["Tiempo en VSC (Hrs)"] = (
        data["Fecha de resolución"]
        - data["Fecha atendió Facturación"]
    ).dt.total_seconds() / 3600

    data["Tiempo total caso (Hrs)"] = (
        data["Fecha de resolución"]
        - data["Fecha de apertura"]
    ).dt.total_seconds() / 3600

    data["Tiempo en Facturación (Hrs)"] = (
        data["Fecha atendió Facturación"]
        - data["Fecha de apertura"]
    ).dt.total_seconds() / 3600

    data = data[
        (data["Tiempo en VSC (Hrs)"] >= 0)
        & (data["Tiempo total caso (Hrs)"] >= 0)
        & (data["Tiempo en Facturación (Hrs)"] >= 0)
    ].copy()

    data["Año"] = data["Fecha de apertura"].dt.year

    data["Semana"] = (
        data["Fecha de apertura"]
        .dt.isocalendar()
        .week
        .astype(int)
    )

    data["Mes"] = (
        data["Fecha de apertura"]
        .dt.to_period("M")
        .astype(str)
    )

    data["Hora apertura"] = (
        data["Fecha de apertura"].dt.hour
    )

    data["Día semana"] = (
        data["Fecha de apertura"]
        .dt.day_name()
        .replace(WEEKDAY_TRANSLATION)
    )

    data["Día semana"] = pd.Categorical(
        data["Día semana"],
        categories=WEEKDAY_ORDER,
        ordered=True,
    )

    data["Rango SLA"] = pd.cut(
        data["Tiempo en VSC (Hrs)"],
        bins=[
            float("-inf"),
            0.5,
            1,
            float("inf"),
        ],
        labels=[
            "Hasta 30 min",
            "Entre 30 min y 1 hora",
            "Más de 1 hora",
        ],
    )

    return data
