import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


def create_weekly_volume_chart(
    df: pd.DataFrame,
) -> go.Figure:
    cases_by_week = (
        df.groupby("Semana")
        .size()
        .rename("Casos")
        .reset_index()
        .sort_values("Semana")
    )

    weeks = sorted(
        cases_by_week["Semana"].unique()
    )

    figure = px.bar(
        cases_by_week,
        x="Semana",
        y="Casos",
        text="Casos",
        title="Volumen de casos por semana",
    )

    figure.update_traces(
        textposition="outside"
    )

    figure.update_xaxes(
        tickmode="array",
        tickvals=weeks,
        ticktext=[
            str(week)
            for week in weeks
        ],
    )

    figure.update_layout(
        xaxis_title="Número de semana",
        yaxis_title="Número de casos",
        showlegend=False,
    )

    return figure


def create_sla_distribution_chart(
    df: pd.DataFrame,
) -> go.Figure:
    sla_distribution = (
        df["Rango SLA"]
        .value_counts(sort=False)
        .rename_axis("Rango")
        .reset_index(name="Casos")
    )

    figure = px.pie(
        sla_distribution,
        names="Rango",
        values="Casos",
        hole=0.55,
        title="Distribución del cumplimiento de SLA",
    )

    figure.update_traces(
        textposition="inside",
        textinfo="percent+label",
    )

    return figure


def create_capacity_chart(
    weekly_report: pd.DataFrame,
) -> go.Figure:
    weeks = sorted(
        weekly_report["Semana"].unique()
    )

    figure = go.Figure()

    figure.add_trace(
        go.Scatter(
            x=weekly_report["Semana"],
            y=weekly_report["Horas_consumidas"],
            mode="lines+markers",
            name="Horas consumidas",
        )
    )

    figure.add_trace(
        go.Scatter(
            x=weekly_report["Semana"],
            y=weekly_report[
                "Capacidad efectiva (Hrs)"
            ],
            mode="lines",
            line={"dash": "dash"},
            name="Capacidad efectiva",
        )
    )

    figure.update_xaxes(
        tickmode="array",
        tickvals=weeks,
        ticktext=[
            str(week)
            for week in weeks
        ],
    )

    figure.update_layout(
        title="Capacidad efectiva vs. horas consumidas",
        xaxis_title="Número de semana",
        yaxis_title="Horas",
    )

    return figure
