from __future__ import annotations

import pandas as pd


# ============================================================
# CONFIGURACIÓN
# ============================================================

CAPACITY_PER_WEEK = 47


# ============================================================
# VALIDACIONES
# ============================================================

REQUIRED_METRIC_COLUMNS = [
    "Semana",
    "Tiempo en VSC (Hrs)",
    "Tiempo en Facturación (Hrs)",
    "Tipo de caso PC",
]


def validate_metric_columns(df: pd.DataFrame) -> None:
    """
    Valida que el DataFrame contenga las columnas necesarias
    para calcular los KPIs.

    Parameters
    ----------
    df:
        DataFrame preparado con la información de los casos.

    Raises
    ------
    ValueError
        Si falta alguna columna requerida.
    """
    missing_columns = [
        column
        for column in REQUIRED_METRIC_COLUMNS
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "No es posible calcular las métricas. "
            "Faltan las columnas: "
            + ", ".join(missing_columns)
        )


# ============================================================
# KPIs GENERALES
# ============================================================

def calculate_general_kpis(
    df: pd.DataFrame,
) -> dict[str, float]:
    """
    Calcula los principales KPIs ejecutivos del periodo filtrado.

    Los rangos de atención son excluyentes:

    - Hasta 30 minutos.
    - Más de 30 y hasta 60 minutos.
    - Más de 60 minutos.

    Parameters
    ----------
    df:
        DataFrame preparado y filtrado.

    Returns
    -------
    dict[str, float]
        Diccionario con los KPIs generales.
    """
    validate_metric_columns(df)

    if df.empty:
        return {
            "total_cases": 0,
            "average_time": 0.0,
            "median_time": 0.0,
            "maximum_time": 0.0,
            "average_wait": 0.0,
            "hours_consumed": 0.0,
            "cases_30_min": 0,
            "cases_30_60_min": 0,
            "cases_over_60_min": 0,
            "pct_30_min": 0.0,
            "pct_30_60_min": 0.0,
            "pct_over_60_min": 0.0,
            "sla_30": 0.0,
            "sla_1_hour": 0.0,
            "over_1_hour": 0.0,
            "capacity_utilization": 0.0,
        }

    total_cases = len(df)

    time_values = df["Tiempo en VSC (Hrs)"]

    cases_30_min = (
        time_values
        .le(0.5)
        .sum()
    )

    cases_30_60_min = (
        (
            (time_values > 0.5)
            & (time_values <= 1)
        ).sum()
    )

    cases_over_60_min = (
        time_values
        .gt(1)
        .sum()
    )

    pct_30_min = (
        cases_30_min
        / total_cases
        * 100
    )

    pct_30_60_min = (
        cases_30_60_min
        / total_cases
        * 100
    )

    pct_over_60_min = (
        cases_over_60_min
        / total_cases
        * 100
    )

    number_of_weeks = max(
        df["Semana"].nunique(),
        1,
    )

    hours_consumed = (
        time_values.sum()
    )

    available_capacity = (
        number_of_weeks
        * CAPACITY_PER_WEEK
    )

    capacity_utilization = (
        hours_consumed
        / available_capacity
        * 100
        if available_capacity > 0
        else 0.0
    )

    return {
        "total_cases": total_cases,

        "average_time": (
            time_values.mean()
        ),

        "median_time": (
            time_values.median()
        ),

        "maximum_time": (
            time_values.max()
        ),

        "average_wait": (
            df["Tiempo en Facturación (Hrs)"]
            .mean()
        ),

        "hours_consumed": hours_consumed,

        "cases_30_min": int(cases_30_min),

        "cases_30_60_min": int(
            cases_30_60_min
        ),

        "cases_over_60_min": int(
            cases_over_60_min
        ),

        "pct_30_min": pct_30_min,

        "pct_30_60_min": (
            pct_30_60_min
        ),

        "pct_over_60_min": (
            pct_over_60_min
        ),

        # Se conservan estas claves para no romper app.py
        "sla_30": pct_30_min,

        "sla_1_hour": (
            pct_30_min
            + pct_30_60_min
        ),

        "over_1_hour": (
            pct_over_60_min
        ),

        "capacity_utilization": (
            capacity_utilization
        ),
    }


# ============================================================
# REPORTE SEMANAL
# ============================================================

def create_weekly_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera un reporte semanal de volumen, tiempos,
    distribución de SLA y utilización de capacidad.

    Los porcentajes de los tres rangos deben sumar
    aproximadamente 100 % por semana.

    Parameters
    ----------
    df:
        DataFrame preparado y filtrado.

    Returns
    -------
    pd.DataFrame
        Reporte semanal consolidado.
    """
    validate_metric_columns(df)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Semana",
                "Casos",
                "Casos_hasta_30_min",
                "Pct_hasta_30_min",
                "Casos_30_a_60_min",
                "Pct_30_a_60_min",
                "Casos_mayores_60_min",
                "Pct_mayores_60_min",
                "Tiempo_promedio",
                "Mediana",
                "Tiempo_maximo",
                "Espera_promedio",
                "Horas_consumidas",
                "Capacidad efectiva (Hrs)",
                "Capacidad disponible (Hrs)",
                "Utilización (%)",
            ]
        )

    report = (
        df.groupby("Semana")
        .agg(
            Casos=(
                "Tiempo en VSC (Hrs)",
                "size",
            ),

            Casos_hasta_30_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    values.le(0.5).sum()
                ),
            ),

            Casos_30_a_60_min=(
                "Tiempo en VSC (Hrs)",
                lambda x: (
                    (
                        (x > 0.5)
                        & (x <= 1)
                    ).sum()
                ),
            ),

            Casos_mayores_60_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    values.gt(1).sum()
                ),
            ),

            Tiempo_promedio=(
                "Tiempo en VSC (Hrs)",
                "mean",
            ),

            Mediana=(
                "Tiempo en VSC (Hrs)",
                "median",
            ),

            Tiempo_maximo=(
                "Tiempo en VSC (Hrs)",
                "max",
            ),

            Espera_promedio=(
                "Tiempo en Facturación (Hrs)",
                "mean",
            ),

            Horas_consumidas=(
                "Tiempo en VSC (Hrs)",
                "sum",
            ),
        )
        .reset_index()
    )

    report["Pct_hasta_30_min"] = (
        report["Casos_hasta_30_min"]
        / report["Casos"]
        * 100
    )

    report["Pct_30_a_60_min"] = (
        report["Casos_30_a_60_min"]
        / report["Casos"]
        * 100
    )

    report["Pct_mayores_60_min"] = (
        report["Casos_mayores_60_min"]
        / report["Casos"]
        * 100
    )

    report["Capacidad efectiva (Hrs)"] = (
        CAPACITY_PER_WEEK
    )

    report["Capacidad disponible (Hrs)"] = (
        report["Capacidad efectiva (Hrs)"]
        - report["Horas_consumidas"]
    )

    report["Utilización (%)"] = (
        report["Horas_consumidas"]
        / report["Capacidad efectiva (Hrs)"]
        * 100
    )

    report["Validación SLA (%)"] = (
        report["Pct_hasta_30_min"]
        + report["Pct_30_a_60_min"]
        + report["Pct_mayores_60_min"]
    )

    report = report[
        [
            "Semana",
            "Casos",

            "Casos_hasta_30_min",
            "Pct_hasta_30_min",

            "Casos_30_a_60_min",
            "Pct_30_a_60_min",

            "Casos_mayores_60_min",
            "Pct_mayores_60_min",

            "Tiempo_promedio",
            "Mediana",
            "Tiempo_maximo",
            "Espera_promedio",

            "Horas_consumidas",
            "Capacidad efectiva (Hrs)",
            "Capacidad disponible (Hrs)",
            "Utilización (%)",

            "Validación SLA (%)",
        ]
    ]

    numeric_columns = [
        "Pct_hasta_30_min",
        "Pct_30_a_60_min",
        "Pct_mayores_60_min",
        "Tiempo_promedio",
        "Mediana",
        "Tiempo_maximo",
        "Espera_promedio",
        "Horas_consumidas",
        "Capacidad disponible (Hrs)",
        "Utilización (%)",
        "Validación SLA (%)",
    ]

    report[numeric_columns] = (
        report[numeric_columns]
        .round(2)
    )

    return report


# ============================================================
# REPORTE POR TIPO DE CASO
# ============================================================

def create_case_type_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera un reporte de desempeño por tipo de caso.

    Parameters
    ----------
    df:
        DataFrame preparado y filtrado.

    Returns
    -------
    pd.DataFrame
        Reporte por tipo de caso.
    """
    validate_metric_columns(df)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "Tipo de caso PC",
                "Casos",
                "Casos_hasta_30_min",
                "Pct_hasta_30_min",
                "Casos_30_a_60_min",
                "Pct_30_a_60_min",
                "Casos_mayores_60_min",
                "Pct_mayores_60_min",
                "Tiempo_promedio",
                "Mediana",
                "Tiempo_maximo",
                "Horas_consumidas",
            ]
        )

    report = (
        df.groupby("Tipo de caso PC")
        .agg(
            Casos=(
                "Tiempo en VSC (Hrs)",
                "size",
            ),

            Casos_hasta_30_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    values.le(0.5).sum()
                ),
            ),

            Casos_30_a_60_min=(
                "Tiempo en VSC (Hrs)",
                lambda x: (
                    (
                        (x > 0.5)
                        & (x <= 1)
                    ).sum()
                ),
            ),

            Casos_mayores_60_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    values.gt(1).sum()
                ),
            ),

            Tiempo_promedio=(
                "Tiempo en VSC (Hrs)",
                "mean",
            ),

            Mediana=(
                "Tiempo en VSC (Hrs)",
                "median",
            ),

            Tiempo_maximo=(
                "Tiempo en VSC (Hrs)",
                "max",
            ),

            Horas_consumidas=(
                "Tiempo en VSC (Hrs)",
                "sum",
            ),
        )
        .reset_index()
    )

    report["Pct_hasta_30_min"] = (
        report["Casos_hasta_30_min"]
        / report["Casos"]
        * 100
    )

    report["Pct_30_a_60_min"] = (
        report["Casos_30_a_60_min"]
        / report["Casos"]
        * 100
    )

    report["Pct_mayores_60_min"] = (
        report["Casos_mayores_60_min"]
        / report["Casos"]
        * 100
    )

    report["Validación SLA (%)"] = (
        report["Pct_hasta_30_min"]
        + report["Pct_30_a_60_min"]
        + report["Pct_mayores_60_min"]
    )

    report = report[
        [
            "Tipo de caso PC",
            "Casos",

            "Casos_hasta_30_min",
            "Pct_hasta_30_min",

            "Casos_30_a_60_min",
            "Pct_30_a_60_min",

            "Casos_mayores_60_min",
            "Pct_mayores_60_min",

            "Tiempo_promedio",
            "Mediana",
            "Tiempo_maximo",
            "Horas_consumidas",

            "Validación SLA (%)",
        ]
    ]

    numeric_columns = [
        "Pct_hasta_30_min",
        "Pct_30_a_60_min",
        "Pct_mayores_60_min",
        "Tiempo_promedio",
        "Mediana",
        "Tiempo_maximo",
        "Horas_consumidas",
        "Validación SLA (%)",
    ]

    report[numeric_columns] = (
        report[numeric_columns]
        .round(2)
    )

    return (
        report
        .sort_values(
            "Casos",
            ascending=False,
        )
        .reset_index(drop=True)
    )


def create_user_performance_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera un reporte de desempeño agrupado por el usuario
    registrado en la columna 'Resuelto por'.

    El reporte incluye volumen, tiempos en VSC y distribución
    de los casos en tres rangos excluyentes:

    - Hasta 30 minutos.
    - Más de 30 y hasta 60 minutos.
    - Más de 60 minutos.

    Parameters
    ----------
    df:
        DataFrame preparado y filtrado.

    Returns
    -------
    pd.DataFrame
        Reporte de performance por persona.
    """
    required_columns = [
        "Resuelto por",
        "Tiempo en VSC (Hrs)",
        "Tiempo en Facturación (Hrs)",
    ]

    missing_columns = [
        column
        for column in required_columns
        if column not in df.columns
    ]

    if missing_columns:
        raise ValueError(
            "No es posible generar el reporte del personal. "
            "Faltan las columnas: "
            + ", ".join(missing_columns)
        )

    data = df.dropna(
        subset=[
            "Resuelto por",
            "Tiempo en VSC (Hrs)",
        ]
    ).copy()

    data["Resuelto por"] = (
        data["Resuelto por"]
        .astype(str)
        .str.strip()
    )

    data = data[
        data["Resuelto por"].ne("")
        & data["Resuelto por"].ne("nan")
    ].copy()

    if data.empty:
        return pd.DataFrame(
            columns=[
                "Resuelto por",
                "Casos",
                "Horas_consumidas",
                "Casos_por_hora",
                "Tiempo_promedio_VSC",
                "Mediana_VSC",
                "Tiempo_maximo_VSC",
                "Tiempo_promedio_Facturacion",
                "Casos_hasta_30_min",
                "Pct_hasta_30_min",
                "Casos_30_a_60_min",
                "Pct_30_a_60_min",
                "Casos_mayores_60_min",
                "Pct_mayores_60_min",
                "Validación SLA (%)",
            ]
        )

    report = (
        data.groupby(
            "Resuelto por",
            dropna=False,
        )
        .agg(
            Casos=(
                "Tiempo en VSC (Hrs)",
                "size",
            ),

            Horas_consumidas=(
                "Tiempo en VSC (Hrs)",
                "sum",
            ),

            Tiempo_promedio_VSC=(
                "Tiempo en VSC (Hrs)",
                "mean",
            ),

            Mediana_VSC=(
                "Tiempo en VSC (Hrs)",
                "median",
            ),

            Tiempo_maximo_VSC=(
                "Tiempo en VSC (Hrs)",
                "max",
            ),

            Tiempo_promedio_Facturacion=(
                "Tiempo en Facturación (Hrs)",
                "mean",
            ),

            Casos_hasta_30_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    values <= 0.5
                ).sum(),
            ),

            Casos_30_a_60_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    (values > 0.5)
                    & (values <= 1)
                ).sum(),
            ),

            Casos_mayores_60_min=(
                "Tiempo en VSC (Hrs)",
                lambda values: (
                    values > 1
                ).sum(),
            ),
        )
        .reset_index()
    )

    report["Casos_por_hora"] = (
        report["Casos"]
        / report["Horas_consumidas"]
    )

    report["Pct_hasta_30_min"] = (
        report["Casos_hasta_30_min"]
        / report["Casos"]
        * 100
    )

    report["Pct_30_a_60_min"] = (
        report["Casos_30_a_60_min"]
        / report["Casos"]
        * 100
    )

    report["Pct_mayores_60_min"] = (
        report["Casos_mayores_60_min"]
        / report["Casos"]
        * 100
    )

    report["Validación SLA (%)"] = (
        report["Pct_hasta_30_min"]
        + report["Pct_30_a_60_min"]
        + report["Pct_mayores_60_min"]
    )

    numeric_columns = [
        "Horas_consumidas",
        "Casos_por_hora",
        "Tiempo_promedio_VSC",
        "Mediana_VSC",
        "Tiempo_maximo_VSC",
        "Tiempo_promedio_Facturacion",
        "Pct_hasta_30_min",
        "Pct_30_a_60_min",
        "Pct_mayores_60_min",
        "Validación SLA (%)",
    ]

    report[numeric_columns] = (
        report[numeric_columns]
        .round(2)
    )

    report = report[
        [
            "Resuelto por",
            "Casos",
            "Horas_consumidas",
            "Casos_por_hora",
            "Tiempo_promedio_VSC",
            "Mediana_VSC",
            "Tiempo_maximo_VSC",
            "Tiempo_promedio_Facturacion",
            "Casos_hasta_30_min",
            "Pct_hasta_30_min",
            "Casos_30_a_60_min",
            "Pct_30_a_60_min",
            "Casos_mayores_60_min",
            "Pct_mayores_60_min",
            "Validación SLA (%)",
        ]
    ]

    return (
        report
        .sort_values(
            "Casos",
            ascending=False,
        )
        .reset_index(drop=True)
    )
