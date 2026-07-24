"""
Funciones para calcular métricas y reportes del dashboard CRM VSC.
"""

import pandas as pd


VSC_TIME_COLUMN = "Tiempo en VSC (Hrs)"
DEFAULT_WEEKLY_CAPACITY_HOURS = 48.0


def safe_percentage(
    numerator: int | float,
    denominator: int | float,
) -> float:
    """
    Calcula un porcentaje evitando división entre cero.
    """

    if denominator == 0:
        return 0.0

    return numerator / denominator * 100


def validate_metric_columns(
    data: pd.DataFrame,
    required_columns: list[str],
) -> None:
    """
    Valida que existan las columnas requeridas.
    """

    missing_columns = [
        column
        for column in required_columns
        if column not in data.columns
    ]

    if missing_columns:
        raise ValueError(
            "No se pueden calcular las métricas. "
            "Faltan las columnas: "
            + ", ".join(missing_columns)
        )


def calculate_time_distribution(
    time_values: pd.Series,
) -> dict[str, float | int]:
    """
    Calcula rangos de tiempo mutuamente excluyentes.
    """

    valid_values = pd.to_numeric(
        time_values,
        errors="coerce",
    ).dropna()

    total_cases = len(valid_values)

    cases_up_to_30 = (
        valid_values <= 0.5
    ).sum()

    cases_30_to_60 = (
        (valid_values > 0.5)
        & (valid_values <= 1.0)
    ).sum()

    cases_over_60 = (
        valid_values > 1.0
    ).sum()

    pct_up_to_30 = safe_percentage(
        cases_up_to_30,
        total_cases,
    )

    pct_30_to_60 = safe_percentage(
        cases_30_to_60,
        total_cases,
    )

    pct_over_60 = safe_percentage(
        cases_over_60,
        total_cases,
    )

    return {
        "Casos_hasta_30_min": int(
            cases_up_to_30
        ),
        "Pct_hasta_30_min": pct_up_to_30,
        "Casos_30_a_60_min": int(
            cases_30_to_60
        ),
        "Pct_30_a_60_min": pct_30_to_60,
        "Casos_mayores_60_min": int(
            cases_over_60
        ),
        "Pct_mayores_60_min": pct_over_60,
        "Validacion_SLA": (
            pct_up_to_30
            + pct_30_to_60
            + pct_over_60
        ),
    }


def calculate_general_kpis(
    data: pd.DataFrame,
) -> dict[str, float | int]:
    """
    Calcula los indicadores generales.
    """

    if data.empty:
        return {
            "total_cases": 0,
            "average_vsc_time": 0.0,
            "median_vsc_time": 0.0,
            "maximum_vsc_time": 0.0,
            "total_vsc_hours": 0.0,
            "pct_30_min": 0.0,
            "pct_30_60_min": 0.0,
            "pct_over_60_min": 0.0,
        }

    validate_metric_columns(
        data,
        [VSC_TIME_COLUMN],
    )

    time_values = pd.to_numeric(
        data[VSC_TIME_COLUMN],
        errors="coerce",
    ).dropna()

    distribution = calculate_time_distribution(
        time_values
    )

    return {
        "total_cases": int(len(data)),
        "average_vsc_time": float(
            time_values.mean()
        ),
        "median_vsc_time": float(
            time_values.median()
        ),
        "maximum_vsc_time": float(
            time_values.max()
        ),
        "total_vsc_hours": float(
            time_values.sum()
        ),
        "pct_30_min": float(
            distribution["Pct_hasta_30_min"]
        ),
        "pct_30_60_min": float(
            distribution["Pct_30_a_60_min"]
        ),
        "pct_over_60_min": float(
            distribution["Pct_mayores_60_min"]
        ),
    }


def create_weekly_report(
    data: pd.DataFrame,
    weekly_capacity_hours: float = (
        DEFAULT_WEEKLY_CAPACITY_HOURS
    ),
) -> pd.DataFrame:
    """
    Genera el reporte semanal usando el número de semana.

    La agrupación se realiza por Año y Semana para evitar
    mezclar la misma semana de años diferentes.
    """

    report_columns = [
        "Año",
        "Semana",
        "Casos",
        "Horas_consumidas",
        "Tiempo_promedio_VSC",
        "Mediana_VSC",
        "Tiempo_maximo_VSC",
        "Capacidad_horas",
        "Utilizacion_pct",
        "Casos_hasta_30_min",
        "Pct_hasta_30_min",
        "Casos_30_a_60_min",
        "Pct_30_a_60_min",
        "Casos_mayores_60_min",
        "Pct_mayores_60_min",
        "Validacion_SLA",
    ]

    if data.empty:
        return pd.DataFrame(
            columns=report_columns
        )

    validate_metric_columns(
        data,
        [
            "Año",
            "Semana",
            VSC_TIME_COLUMN,
        ],
    )

    weekly_rows = []

    grouped_data = data.groupby(
        [
            "Año",
            "Semana",
        ],
        dropna=False,
        observed=True,
    )

    for (year, week), group in grouped_data:
        time_values = pd.to_numeric(
            group[VSC_TIME_COLUMN],
            errors="coerce",
        ).dropna()

        distribution = calculate_time_distribution(
            time_values
        )

        consumed_hours = float(
            time_values.sum()
        )

        utilization = safe_percentage(
            consumed_hours,
            weekly_capacity_hours,
        )

        weekly_rows.append(
            {
                "Año": int(year),
                "Semana": int(week),
                "Casos": int(len(group)),
                "Horas_consumidas": consumed_hours,
                "Tiempo_promedio_VSC": float(
                    time_values.mean()
                ),
                "Mediana_VSC": float(
                    time_values.median()
                ),
                "Tiempo_maximo_VSC": float(
                    time_values.max()
                ),
                "Capacidad_horas": float(
                    weekly_capacity_hours
                ),
                "Utilizacion_pct": utilization,
                **distribution,
            }
        )

    weekly_report = pd.DataFrame(
        weekly_rows
    )

    weekly_report = weekly_report[
        report_columns
    ]

    numeric_columns = (
        weekly_report
        .select_dtypes(include="number")
        .columns
    )

    weekly_report[numeric_columns] = (
        weekly_report[numeric_columns]
        .round(2)
    )

    return weekly_report.sort_values(
        [
            "Año",
            "Semana",
        ]
    ).reset_index(
        drop=True
    )


def create_case_type_report(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera indicadores por tipo de caso.
    """

    report_columns = [
        "Tipo de caso PC",
        "Casos",
        "Horas_consumidas",
        "Tiempo_promedio_VSC",
        "Mediana_VSC",
        "Tiempo_maximo_VSC",
        "Casos_hasta_30_min",
        "Pct_hasta_30_min",
        "Casos_30_a_60_min",
        "Pct_30_a_60_min",
        "Casos_mayores_60_min",
        "Pct_mayores_60_min",
        "Validacion_SLA",
    ]

    if data.empty:
        return pd.DataFrame(
            columns=report_columns
        )

    validate_metric_columns(
        data,
        [
            "Tipo de caso PC",
            VSC_TIME_COLUMN,
        ],
    )

    report_rows = []

    grouped_data = data.groupby(
        "Tipo de caso PC",
        dropna=False,
        observed=True,
    )

    for case_type, group in grouped_data:
        time_values = pd.to_numeric(
            group[VSC_TIME_COLUMN],
            errors="coerce",
        ).dropna()

        distribution = calculate_time_distribution(
            time_values
        )

        report_rows.append(
            {
                "Tipo de caso PC": (
                    case_type
                    if pd.notna(case_type)
                    else "Sin clasificación"
                ),
                "Casos": int(len(group)),
                "Horas_consumidas": float(
                    time_values.sum()
                ),
                "Tiempo_promedio_VSC": float(
                    time_values.mean()
                ),
                "Mediana_VSC": float(
                    time_values.median()
                ),
                "Tiempo_maximo_VSC": float(
                    time_values.max()
                ),
                **distribution,
            }
        )

    case_type_report = pd.DataFrame(
        report_rows
    )

    case_type_report = case_type_report[
        report_columns
    ]

    numeric_columns = (
        case_type_report
        .select_dtypes(include="number")
        .columns
    )

    case_type_report[numeric_columns] = (
        case_type_report[numeric_columns]
        .round(2)
    )

    return case_type_report.sort_values(
        "Casos",
        ascending=False,
    ).reset_index(
        drop=True
    )


def create_user_performance_report(
    data: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera indicadores agrupados por 'Resuelto por'.
    """

    report_columns = [
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
        "Validacion_SLA",
    ]

    if data.empty:
        return pd.DataFrame(
            columns=report_columns
        )

    validate_metric_columns(
        data,
        [
            "Resuelto por",
            VSC_TIME_COLUMN,
        ],
    )

    performance_data = data[
        data["Resuelto por"].notna()
    ].copy()

    if performance_data.empty:
        return pd.DataFrame(
            columns=report_columns
        )

    report_rows = []

    grouped_data = performance_data.groupby(
        "Resuelto por",
        dropna=False,
        observed=True,
    )

    for user, group in grouped_data:
        time_values = pd.to_numeric(
            group[VSC_TIME_COLUMN],
            errors="coerce",
        ).dropna()

        distribution = calculate_time_distribution(
            time_values
        )

        total_cases = int(len(group))
        consumed_hours = float(
            time_values.sum()
        )

        cases_per_hour = (
            total_cases / consumed_hours
            if consumed_hours > 0
            else 0.0
        )

        if (
            "Tiempo en Facturación (Hrs)"
            in group.columns
        ):
            billing_values = pd.to_numeric(
                group[
                    "Tiempo en Facturación (Hrs)"
                ],
                errors="coerce",
            ).dropna()

            average_billing_time = float(
                billing_values.mean()
            )
        else:
            average_billing_time = 0.0

        report_rows.append(
            {
                "Resuelto por": str(user),
                "Casos": total_cases,
                "Horas_consumidas": consumed_hours,
                "Casos_por_hora": cases_per_hour,
                "Tiempo_promedio_VSC": float(
                    time_values.mean()
                ),
                "Mediana_VSC": float(
                    time_values.median()
                ),
                "Tiempo_maximo_VSC": float(
                    time_values.max()
                ),
                "Tiempo_promedio_Facturacion": (
                    average_billing_time
                ),
                **distribution,
            }
        )

    performance_report = pd.DataFrame(
        report_rows
    )

    performance_report = performance_report[
        report_columns
    ]

    numeric_columns = (
        performance_report
        .select_dtypes(include="number")
        .columns
    )

    performance_report[numeric_columns] = (
        performance_report[numeric_columns]
        .round(2)
    )

    return performance_report.sort_values(
        "Casos",
        ascending=False,
    ).reset_index(
        drop=True
    )
