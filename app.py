from io import BytesIO

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from src.data_loader import load_cases_data
from src.metrics import (
    calculate_general_kpis,
    create_case_type_report,
    create_user_performance_report,
    create_weekly_report,
)
from src.preprocessing import prepare_cases_data

from src.config import APP_NAME, VERSION


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="CRM VSC | Executive Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

@st.cache_data(show_spinner=False)
def get_data(
    uploaded_file,
) -> tuple[pd.DataFrame, dict, pd.DataFrame]:
    """
    Carga y prepara el archivo seleccionado por el usuario.
    """

    raw_data = load_cases_data(uploaded_file)

    return prepare_cases_data(raw_data)


def dataframe_to_excel(
    dataframe: pd.DataFrame,
    sheet_name: str = "Datos",
) -> bytes:
    """
    Convierte un DataFrame en un archivo Excel descargable.
    """

    output = BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:
        dataframe.to_excel(
            writer,
            index=False,
            sheet_name=sheet_name,
        )

    return output.getvalue()


def get_existing_columns(
    dataframe: pd.DataFrame,
    preferred_columns: list[str],
) -> list[str]:
    """
    Devuelve únicamente las columnas disponibles.
    """

    return [
        column
        for column in preferred_columns
        if column in dataframe.columns
    ]


# ============================================================
# ENCABEZADO
# ============================================================

st.title("CRM VSC — Executive Dashboard")

st.caption(
    "Análisis de casos, tiempos de procesamiento, capacidad, "
    "performance del personal y calidad de datos."
)

st.markdown(
    """
    <div style="
        padding: 14px 18px;
        margin: 12px 0 20px 0;
        background-color: #f3f4f6;
        border-left: 4px solid #6b7280;
        border-radius: 10px;
        color: #1f2937;
        font-size: 0.95rem;
        line-height: 1.6;
    ">
        <strong>Supuesto de capacidad:</strong>
        se consideran 47 horas semanales disponibles para la atención de casos.
        Este valor representa aproximadamente el 50 % de la capacidad total de
        dos recursos; el tiempo restante se destina a seguimiento, coordinación
        y administración de proyectos.
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================
# CARGA DEL ARCHIVO
# ============================================================

st.sidebar.header("Fuente de datos")

uploaded_file = st.sidebar.file_uploader(
    label="Selecciona el archivo Excel",
    type=["xlsx", "xls"],
    help="Carga el archivo exportado desde CRM.",
)

if uploaded_file is None:
    st.info(
        "Carga un archivo Excel desde la barra lateral "
        "para visualizar el dashboard."
    )
    st.stop()


try:
    with st.spinner("Cargando y preparando la información..."):
        (
            df_cases,
            cleaning_stats,
            discarded_data,
        ) = get_data(uploaded_file)

except ValueError as error:
    st.error(
        f"El archivo no cumple con la estructura requerida: {error}"
    )
    st.stop()

except Exception as error:
    st.error(
        f"No fue posible procesar el archivo: {error}"
    )
    st.stop()


if df_cases.empty:
    st.warning(
        "Después del proceso de limpieza no quedaron "
        "registros válidos para analizar."
    )
    st.stop()


# ============================================================
# FILTROS
# ============================================================

filtered_data = df_cases.copy()

st.sidebar.divider()
st.sidebar.header("Filtros")


if (
    "Fecha de apertura" in filtered_data.columns
    and filtered_data["Fecha de apertura"].notna().any()
):
    minimum_date = (
        filtered_data["Fecha de apertura"]
        .dropna()
        .min()
        .date()
    )

    maximum_date = (
        filtered_data["Fecha de apertura"]
        .dropna()
        .max()
        .date()
    )

    selected_dates = st.sidebar.date_input(
        label="Rango de fechas",
        value=(minimum_date, maximum_date),
        min_value=minimum_date,
        max_value=maximum_date,
    )

    if (
        isinstance(selected_dates, tuple)
        and len(selected_dates) == 2
    ):
        start_date, end_date = selected_dates

        filtered_data = filtered_data[
            filtered_data["Fecha de apertura"]
            .dt.date
            .between(start_date, end_date)
        ].copy()


if "Unidad de Negocio" in filtered_data.columns:
    business_units = sorted(
        filtered_data["Unidad de Negocio"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_business_units = st.sidebar.multiselect(
        label="Unidad de Negocio",
        options=business_units,
        default=business_units,
    )

    if selected_business_units:
        filtered_data = filtered_data[
            filtered_data["Unidad de Negocio"]
            .astype(str)
            .isin(selected_business_units)
        ].copy()


if "Tipo de caso PC" in filtered_data.columns:
    case_types = sorted(
        filtered_data["Tipo de caso PC"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_case_types = st.sidebar.multiselect(
        label="Tipo de caso",
        options=case_types,
        default=case_types,
    )

    if selected_case_types:
        filtered_data = filtered_data[
            filtered_data["Tipo de caso PC"]
            .astype(str)
            .isin(selected_case_types)
        ].copy()


if "Resuelto por" in filtered_data.columns:
    personnel_options = sorted(
        filtered_data["Resuelto por"]
        .dropna()
        .astype(str)
        .unique()
        .tolist()
    )

    selected_personnel = st.sidebar.multiselect(
        label="Resuelto por",
        options=personnel_options,
        default=personnel_options,
    )

    if selected_personnel:
        filtered_data = filtered_data[
            filtered_data["Resuelto por"]
            .astype(str)
            .isin(selected_personnel)
        ].copy()


st.sidebar.divider()
st.sidebar.write(
    f"Registros después de filtros: **{len(filtered_data):,}**"
)


if filtered_data.empty:
    st.warning(
        "No existen registros que coincidan con los filtros seleccionados."
    )
    st.stop()


# ============================================================
# REPORTES
# ============================================================

general_kpis = calculate_general_kpis(
    filtered_data
)

weekly_report = create_weekly_report(
    filtered_data
)

case_type_report = create_case_type_report(
    filtered_data
)

user_performance_report = create_user_performance_report(
    filtered_data
)


# ============================================================
# PESTAÑAS
# ============================================================

(
    summary_tab,
    sla_tab,
    capacity_tab,
    case_type_tab,
    personnel_tab,
    data_quality_tab,
    detail_tab,
) = st.tabs(
    [
        "Resumen",
        "SLA y tiempos",
        "Capacidad",
        "Tipos de caso",
        "Performance del personal",
        "Calidad de datos",
        "Detalle",
    ]
)


# ============================================================
# TAB: RESUMEN
# ============================================================

with summary_tab:
    st.subheader("Resumen ejecutivo")

    summary_metrics = st.columns(4)

    summary_metrics[0].metric(
        label="Casos analizados",
        value=f"{general_kpis['total_cases']:,}",
    )

    summary_metrics[1].metric(
        label="Promedio en VSC",
        value=(
            f"{general_kpis['average_vsc_time'] * 60:.1f} min"
        ),
    )

    summary_metrics[2].metric(
        label="Mediana en VSC",
        value=(
            f"{general_kpis['median_vsc_time'] * 60:.1f} min"
        ),
    )

    summary_metrics[3].metric(
        label="Horas acumuladas en VSC",
        value=f"{general_kpis['total_vsc_hours']:.1f} h",
    )

    st.divider()

    sla_metrics = st.columns(3)

    sla_metrics[0].metric(
        label="Hasta 30 min",
        value=f"{general_kpis['pct_30_min']:.1f}%",
    )

    sla_metrics[1].metric(
        label="31 a 60 min",
        value=f"{general_kpis['pct_30_60_min']:.1f}%",
    )

    sla_metrics[2].metric(
        label="Más de 60 min",
        value=f"{general_kpis['pct_over_60_min']:.1f}%",
    )


# ============================================================
# TAB: SLA Y TIEMPOS
# ============================================================

with sla_tab:
    st.subheader("SLA y tiempos por número de semana")

    if weekly_report.empty:
        st.info(
            "No existe información suficiente para generar "
            "el reporte semanal."
        )
    else:
        weekly_long = weekly_report[
            [
                "Año",
                "Semana",
                "Pct_hasta_30_min",
                "Pct_30_a_60_min",
                "Pct_mayores_60_min",
            ]
        ].melt(
            id_vars=[
                "Año",
                "Semana",
            ],
            var_name="Rango",
            value_name="Porcentaje",
        )

        weekly_long["Rango"] = weekly_long[
            "Rango"
        ].replace(
            {
                "Pct_hasta_30_min": "Hasta 30 min",
                "Pct_30_a_60_min": "31 a 60 min",
                "Pct_mayores_60_min": "Más de 60 min",
            }
        )

        fig_weekly_sla = px.bar(
            weekly_long,
            x="Semana",
            y="Porcentaje",
            color="Rango",
            facet_col="Año",
            barmode="stack",
            title="Distribución de tiempos por número de semana",
        )

        weeks = sorted(
            weekly_long["Semana"]
            .dropna()
            .astype(int)
            .unique()
        )

        fig_weekly_sla.update_xaxes(
            type="linear",
            tickmode="linear",
            tick0=min(weeks),
            dtick=1,
        )

        fig_weekly_sla.update_layout(
            xaxis_title="Número de semana",
            yaxis_title="Porcentaje",
            legend_title="Rango",
        )

        fig_weekly_sla.update_yaxes(
            range=[0, 100]
        )

        st.plotly_chart(
            fig_weekly_sla,
            use_container_width=True,
        )

        st.dataframe(
            weekly_report,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB: CAPACIDAD
# ============================================================

with capacity_tab:
    st.subheader("Capacidad por número de semana")

    if weekly_report.empty:
        st.info(
            "No existe información semanal para analizar capacidad."
        )
    else:
        fig_weekly_cases = px.line(
            weekly_report,
            x="Semana",
            y="Casos",
            color="Año",
            markers=True,
            title="Casos procesados por número de semana",
        )

        weeks = sorted(
            weekly_report["Semana"]
            .dropna()
            .astype(int)
            .unique()
        )

        fig_weekly_cases.update_xaxes(
            type="linear",
            tickmode="linear",
            tick0=min(weeks),
            dtick=1,
            tickangle=-45,
        )

        fig_weekly_cases.update_layout(
            xaxis_title="Número de semana",
            yaxis_title="Número de casos",
            legend_title="Año",
        )

        st.plotly_chart(
            fig_weekly_cases,
            use_container_width=True,
        )

        fig_utilization = px.bar(
            weekly_report,
            x="Semana",
            y="Utilizacion_pct",
            color="Año",
            barmode="group",
            text="Utilizacion_pct",
            title="Utilización de capacidad por número de semana",
        )

        fig_utilization.update_xaxes(
            type="linear",
            tickmode="linear",
            tick0=min(weeks),
            dtick=1,
        )

        fig_utilization.update_traces(
            texttemplate="%{text:.1f}%",
            textposition="outside",
        )

        fig_utilization.update_layout(
            xaxis_title="Número de semana",
            yaxis_title="Utilización",
            legend_title="Año",
        )

        st.plotly_chart(
            fig_utilization,
            use_container_width=True,
        )

        st.dataframe(
            weekly_report,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB: TIPOS DE CASO
# ============================================================

with case_type_tab:
    st.subheader("Análisis por tipo de caso")

    if case_type_report.empty:
        st.info(
            "No existe información suficiente para generar "
            "el reporte por tipo de caso."
        )
    else:
        st.dataframe(
            case_type_report,
            use_container_width=True,
            hide_index=True,
        )


# ============================================================
# TAB: PERFORMANCE DEL PERSONAL
# ============================================================

with personnel_tab:
    st.subheader("Performance del personal")

    if user_performance_report.empty:
        st.info(
            "No existen registros válidos en la columna "
            "'Resuelto por'."
        )
    else:
        chart_col_1, chart_col_2 = st.columns(2)

        volume_by_person = (
            user_performance_report
            .sort_values(
                "Casos",
                ascending=True,
            )
        )

        fig_person_volume = px.bar(
            volume_by_person,
            x="Casos",
            y="Resuelto por",
            orientation="h",
            text="Casos",
            title="Casos resueltos por persona",
        )

        fig_person_volume.update_traces(
            textposition="outside",
        )

        chart_col_1.plotly_chart(
            fig_person_volume,
            use_container_width=True,
        )

        hours_by_person = (
            user_performance_report
            .sort_values(
                "Horas_consumidas",
                ascending=True,
            )
        )

        fig_person_hours = px.bar(
            hours_by_person,
            x="Horas_consumidas",
            y="Resuelto por",
            orientation="h",
            text="Horas_consumidas",
            title="Horas acumuladas en VSC",
        )

        fig_person_hours.update_traces(
            texttemplate="%{text:.1f} h",
            textposition="outside",
        )

        chart_col_2.plotly_chart(
            fig_person_hours,
            use_container_width=True,
        )

        st.subheader("Distribución de tiempos por persona")

        maximum_cases = max(
            1,
            int(
                user_performance_report["Casos"].max()
            ),
        )

        minimum_cases = st.slider(
            label=(
                "Mínimo de casos para incluir a la persona "
                "en la comparación"
            ),
            min_value=1,
            max_value=maximum_cases,
            value=min(1, maximum_cases),
        )

        comparable_personnel = (
            user_performance_report[
                user_performance_report["Casos"]
                >= minimum_cases
            ]
            .copy()
            .sort_values(
                "Pct_hasta_30_min",
                ascending=True,
            )
        )

        if not comparable_personnel.empty:
            fig_person_sla = go.Figure()

            fig_person_sla.add_trace(
                go.Bar(
                    y=comparable_personnel["Resuelto por"],
                    x=comparable_personnel["Pct_hasta_30_min"],
                    name="Hasta 30 min",
                    orientation="h",
                )
            )

            fig_person_sla.add_trace(
                go.Bar(
                    y=comparable_personnel["Resuelto por"],
                    x=comparable_personnel["Pct_30_a_60_min"],
                    name="31 a 60 min",
                    orientation="h",
                )
            )

            fig_person_sla.add_trace(
                go.Bar(
                    y=comparable_personnel["Resuelto por"],
                    x=comparable_personnel[
                        "Pct_mayores_60_min"
                    ],
                    name="Más de 60 min",
                    orientation="h",
                )
            )

            fig_person_sla.update_layout(
                barmode="stack",
                xaxis_title="Porcentaje",
                yaxis_title="Personal",
                xaxis_range=[0, 100],
                legend_title="Rango",
            )

            st.plotly_chart(
                fig_person_sla,
                use_container_width=True,
            )

        st.dataframe(
            user_performance_report,
            use_container_width=True,
            hide_index=True,
        )

        # ====================================================
        # ANÁLISIS INDIVIDUAL
        # ====================================================

        st.divider()
        st.subheader("Análisis individual")

        personnel_list = sorted(
            filtered_data["Resuelto por"]
            .dropna()
            .astype(str)
            .unique()
            .tolist()
        )

        selected_person = st.selectbox(
            label="Seleccionar personal",
            options=personnel_list,
            key="individual_personnel_selector",
        )

        individual_data = filtered_data[
            filtered_data["Resuelto por"]
            .astype(str)
            .eq(selected_person)
        ].copy()

        individual_report = (
            user_performance_report[
                user_performance_report["Resuelto por"]
                .astype(str)
                .eq(selected_person)
            ]
        )

        if individual_report.empty:
            st.info(
                "No existe información suficiente para analizar "
                "a la persona seleccionada."
            )
        else:
            individual_metrics = (
                individual_report.iloc[0]
            )

            metric_columns = st.columns(5)

            metric_columns[0].metric(
                label="Casos resueltos",
                value=int(
                    individual_metrics["Casos"]
                ),
            )

            metric_columns[1].metric(
                label="Promedio en VSC",
                value=(
                    f"{individual_metrics['Tiempo_promedio_VSC'] * 60:.1f} min"
                ),
            )

            metric_columns[2].metric(
                label="Mediana en VSC",
                value=(
                    f"{individual_metrics['Mediana_VSC'] * 60:.1f} min"
                ),
            )

            metric_columns[3].metric(
                label="Hasta 30 min",
                value=(
                    f"{individual_metrics['Pct_hasta_30_min']:.1f}%"
                ),
            )

            metric_columns[4].metric(
                label="Más de 60 min",
                value=(
                    f"{individual_metrics['Pct_mayores_60_min']:.1f}%"
                ),
            )

            individual_columns = get_existing_columns(
                individual_data,
                [
                    "Fecha de apertura",
                    "Unidad de Negocio",
                    "Tipo de caso PC",
                    "Tiempo en VSC (Hrs)",
                    "Tiempo en Facturación (Hrs)",
                    "Tiempo total caso (Hrs)",
                    "Rango SLA",
                ],
            )

            individual_detail = (
                individual_data[
                    individual_columns
                ]
                .sort_values(
                    "Fecha de apertura",
                    ascending=False,
                )
                .reset_index(
                    drop=True
                )
            )

            st.dataframe(
                individual_detail,
                use_container_width=True,
                hide_index=True,
            )


# ============================================================
# TAB: CALIDAD DE DATOS
# ============================================================

with data_quality_tab:
    st.subheader("Calidad y depuración de datos")

    quality_metrics = st.columns(4)

    quality_metrics[0].metric(
        label="Registros iniciales",
        value=cleaning_stats["registros_iniciales"],
    )

    quality_metrics[1].metric(
        label="Registros válidos",
        value=cleaning_stats["registros_finales"],
    )

    quality_metrics[2].metric(
        label="Registros descartados",
        value=cleaning_stats["registros_eliminados"],
    )

    quality_metrics[3].metric(
        label="Porcentaje descartado",
        value=(
            f"{cleaning_stats['porcentaje_eliminado']:.2f}%"
        ),
    )

    st.divider()

    if discarded_data.empty:
        st.success(
            "No se descartaron registros."
        )
    else:
        st.subheader("Motivos de descarte")

        discarded_summary = (
            discarded_data["Motivo del descarte"]
            .fillna("Sin motivo identificado")
            .value_counts()
            .rename_axis("Motivo del descarte")
            .reset_index(name="Registros")
        )

        discarded_summary["Porcentaje"] = (
            discarded_summary["Registros"]
            / len(discarded_data)
            * 100
        ).round(2)

        st.dataframe(
            discarded_summary,
            use_container_width=True,
            hide_index=True,
        )

        st.subheader("Registros descartados")

        preferred_columns = [
            "Número de caso",
            "Título",
            "Unidad de Negocio",
            "Tipo de caso PC",
            "Fecha de apertura",
            "Fecha asigno caso",
            "Fecha atendió Facturación",
            "Fecha de resolución",
            "Resuelto por",
            "Motivo del descarte",
        ]

        discarded_columns = get_existing_columns(
            discarded_data,
            preferred_columns,
        )

        if not discarded_columns:
            discarded_columns = (
                discarded_data.columns.tolist()
            )

        st.dataframe(
            discarded_data[discarded_columns],
            use_container_width=True,
            hide_index=True,
        )

        discarded_excel = dataframe_to_excel(
            discarded_data,
            sheet_name="Descartados",
        )

        st.download_button(
            label="Descargar registros descartados",
            data=discarded_excel,
            file_name="registros_descartados.xlsx",
            mime=(
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            ),
        )


# ============================================================
# TAB: DETALLE
# ============================================================

with detail_tab:
    st.subheader("Detalle de casos")

    st.dataframe(
        filtered_data,
        use_container_width=True,
        hide_index=True,
    )

    filtered_excel = dataframe_to_excel(
        filtered_data,
        sheet_name="Casos_filtrados",
    )

    st.download_button(
        label="Descargar datos filtrados",
        data=filtered_excel,
        file_name="casos_filtrados.xlsx",
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


# ============================================================
# FOOTER
# ============================================================

st.sidebar.divider()

st.sidebar.caption(
    f"{APP_NAME}"
)

st.sidebar.caption(
    f"Versión {VERSION}"
)
