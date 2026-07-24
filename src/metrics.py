import pandas as pd


CAPACITY_PER_WEEK = 47


def calculate_general_kpis(
    df: pd.DataFrame,
) -> dict[str, float]:
    """
    Calcula los principales KPIs ejecutivos.
    """
    if df.empty:
        return {
            "total_cases": 0,
            "average_time": 0,
            "median_time": 0,
            "sla_30": 0,
            "sla_1_hour": 0,
            "over_1_hour": 0,
            "average_wait": 0,
            "hours_consumed": 0,
            "capacity_utilization": 0,
        }

    number_of_weeks = max(
        df["Semana"].nunique(),
        1,
    )

    hours_consumed = (
        df["Tiempo atención (Hrs)"].sum()
    )

    available_capacity = (
        number_of_weeks * CAPACITY_PER_WEEK
    )

    return {
        "total_cases": len(df),

        "average_time": (
            df["Tiempo atención (Hrs)"].mean()
        ),

        "median_time": (
            df["Tiempo atención (Hrs)"].median()
        ),

        "sla_30": (
            df["Tiempo atención (Hrs)"]
            .le(0.5)
            .mean()
            * 100
        ),

        "sla_1_hour": (
            df["Tiempo atención (Hrs)"]
            .le(1)
            .mean()
            * 100
        ),

        "over_1_hour": (
            df["Tiempo atención (Hrs)"]
            .gt(1)
            .mean()
            * 100
        ),

        "average_wait": (
            df["Tiempo espera atención (Hrs)"]
            .mean()
        ),

        "hours_consumed": hours_consumed,

        "capacity_utilization": (
            hours_consumed
            / available_capacity
            * 100
        ),
    }


def create_weekly_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera el reporte de desempeño semanal.
    """
    report = (
        df.groupby("Semana")
        .agg(
            Casos=(
                "Tiempo atención (Hrs)",
                "size",
            ),

            Horas_consumidas=(
                "Tiempo atención (Hrs)",
                "sum",
            ),

            Tiempo_promedio=(
                "Tiempo atención (Hrs)",
                "mean",
            ),

            Mediana=(
                "Tiempo atención (Hrs)",
                "median",
            ),

            Tiempo_maximo=(
                "Tiempo atención (Hrs)",
                "max",
            ),

            Espera_promedio=(
                "Tiempo espera atención (Hrs)",
                "mean",
            ),

            Cumplimiento_30_min=(
                "Tiempo atención (Hrs)",
                lambda values: (
                    values.le(0.5).mean() * 100
                ),
            ),

            Cumplimiento_1_hora=(
                "Tiempo atención (Hrs)",
                lambda values: (
                    values.le(1).mean() * 100
                ),
            ),

            Mayores_1_hora_pct=(
                "Tiempo atención (Hrs)",
                lambda values: (
                    values.gt(1).mean() * 100
                ),
            ),
        )
        .round(2)
        .reset_index()
    )

    report["Capacidad efectiva (Hrs)"] = (
        CAPACITY_PER_WEEK
    )

    report["Capacidad disponible (Hrs)"] = (
        report["Capacidad efectiva (Hrs)"]
        - report["Horas_consumidas"]
    ).round(2)

    report["Utilización (%)"] = (
        report["Horas_consumidas"]
        / report["Capacidad efectiva (Hrs)"]
        * 100
    ).round(1)

    return report


def create_case_type_report(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Genera el desempeño por tipo de caso.
    """
    return (
        df.groupby("Tipo de caso PC")
        .agg(
            Casos=(
                "Tiempo atención (Hrs)",
                "size",
            ),

            Horas_consumidas=(
                "Tiempo atención (Hrs)",
                "sum",
            ),

            Tiempo_promedio=(
                "Tiempo atención (Hrs)",
                "mean",
            ),

            Mediana=(
                "Tiempo atención (Hrs)",
                "median",
            ),

            Cumplimiento_30_min=(
                "Tiempo atención (Hrs)",
                lambda values: (
                    values.le(0.5).mean() * 100
                ),
            ),

            Cumplimiento_1_hora=(
                "Tiempo atención (Hrs)",
                lambda values: (
                    values.le(1).mean() * 100
                ),
            ),

            Mayores_1_hora_pct=(
                "Tiempo atención (Hrs)",
                lambda values: (
                    values.gt(1).mean() * 100
                ),
            ),
        )
        .round(2)
        .sort_values(
            "Casos",
            ascending=False,
        )
        .reset_index()
    )
