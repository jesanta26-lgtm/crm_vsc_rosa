from __future__ import annotations

import io

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

from src.charts import (
    create_capacity_chart,
    create_sla_distribution_chart,
    create_weekly_volume_chart,
)
from src.data_loader import load_cases_data

from src.metrics import (
    calculate_general_kpis,
    create_case_type_report,
    create_user_performance_report,
    create_weekly_report,
)
from src.preprocessing import prepare_cases_data


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================

st.set_page_config(
    page_title="Planning Services Dashboard",
    page_icon="📊",
    layout="wide",
)


# ============================================================
# ESTILOS
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
        }

        div[data-testid="stMetric"] {
            background-color: rgba(127, 127, 127, 0.07);
            border: 1px solid rgba(127, 127, 127, 0.18);
            padding: 16px;
            border-radius: 14px;
        }

        div[data-testid="stMetricLabel"] {
            font-size: 0.9rem;
        }

        .dashboard-note {
            padding: 0.8rem 1rem;
            border-radius: 12px;
            background-color: rgba(127, 127, 127, 0.08);
            border-left: 4px solid #6c757d;
            margin-bottom: 1rem;
        }

        .footer {
            text-align: center;
            color: #7a7a7a;
            font-size: 0.8rem;
            margin-top: 2rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

@st.cache_data(show_spinner=False)
def get_data(uploaded_file) -> pd.DataFrame:
    """
    Carga y prepara el archivo seleccionado por el usuario.

    Parameters
    ----------
    uploaded_file:
        Archivo Excel cargado desde Streamlit.

    Returns
    -------
    pd.DataFrame
        Base de casos limpia y preparada.
    """
    raw_data = load_cases_data(uploaded_file)

    return prepare_cases_data(raw_data)


def apply_filters(
    df: pd.DataFrame,
    start_date,
    end_date,
    selected_units: list[str],
    selected_types: list[str],
    selected_responsibles: list[str],
) -> pd.DataFrame:
    """
    Aplica filtros al DataFrame.
    """
    filtered_data = df[
        df["Fecha de apertura"]
        .dt.date
        .between(start_date, end_date)
    ].copy()

    if selected_units:
        filtered_data = filtered_data[
            filtered_data["Unidad de Negocio"]
            .astype(str)
            .isin(selected_units)
        ]

    if selected_types:
        filtered_data = filtered_data[
            filtered_data["Tipo de caso PC"]
            .astype(str)
            .isin(selected_types)
        ]

    if (
        selected_responsibles
        and "Resuelto por" in filtered_data.columns
    ):
        filtered_data = filtered_data[
            filtered_data["Resuelto por"]
            .astype(str)
            .isin(selected_responsibles)
        ]

    return filtered_data


def create_excel_download(
    filtered_data: pd.DataFrame,
    weekly_report: pd.DataFrame,
    case_type_report: pd.DataFrame,
    user_performance_report: pd.DataFrame,
) -> bytes:
    """
    Genera un archivo Excel con los resultados filtrados.
    """
    output = io.BytesIO()

    with pd.ExcelWriter(
        output,
        engine="openpyxl",
    ) as writer:

        filtered_data.to_excel(
            writer,
            sheet_name="Datos filtrados",
            index=False,
        )

        weekly_report.to_excel(
            writer,
            sheet_name="Reporte semanal",
            index=False,
        )

        case_type_report.to_excel(
            writer,
            sheet_name="Reporte por tipo",
            index=False,
        )

        user_performance_report.to_excel(
            writer,
            sheet_name="Performance personal",
            index=False,
        )

    return output.getvalue()


# ============================================================
# ENCABEZADO
# ============================================================

st.title("📊 Planning Services Executive Dashboard")

st.caption(
    "Análisis ejecutivo del volumen de casos, tiempos de atención, "
    "cumplimiento de SLA y utilización de capacidad."
)

st.markdown(
    """
    <div class="dashboard-note">
        <b>Supuesto de capacidad:</b>
        se consideran 47 horas semanales disponibles para la atención
        de casos. Este valor representa aproximadamente el 50 % de la
        capacidad total de dos recursos; el tiempo restante se destina
        a seguimiento, coordinación y administración de proyectos.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# CARGA DE ARCHIVO
# ============================================================

st.sidebar.header("Carga de información")

uploaded_file = st.sidebar.file_uploader(
    label="Cargar archivo de casos",
    type=["xlsx"],
    help=(
        "Selecciona el archivo Excel exportado desde CRM "
        "con los casos de Planning Services."
    ),
)


if uploaded_file is None:
    st.info(
        "Carga un archivo Excel desde el panel lateral "
        "para visualizar el dashboard."
    )

    st.stop()


try:
    with st.spinner("Procesando archivo..."):
        df_cases = get_data(uploaded_file)

except ValueError as error:
    st.error(str(error))
    st.stop()

except RuntimeError as error:
    st.error(str(error))
    st.stop()

except Exception as error:
    st.error(
        "Ocurrió un error inesperado al procesar el archivo: "
        f"{error}"
    )
    st.stop()


if df_cases.empty:
    st.warning(
        "El archivo fue cargado, pero no contiene registros "
        "válidos después de la preparación de los datos."
    )

    st.stop()


st.sidebar.success(
    f"Archivo cargado: {uploaded_file.name}"
)


# ============================================================
# FILTROS
# ============================================================

st.sidebar.header("Filtros")

minimum_date = (
    df_cases["Fecha de apertura"]
    .min()
    .date()
)

maximum_date = (
    df_cases["Fecha de apertura"]
    .max()
    .date()
)

selected_date_range = st.sidebar.date_input(
    label="Periodo",
    value=(minimum_date, maximum_date),
    min_value=minimum_date,
    max_value=maximum_date,
)


if (
    isinstance(selected_date_range, tuple)
    and len(selected_date_range) == 2
):
    start_date, end_date = selected_date_range

else:
    start_date = selected_date_range
    end_date = selected_date_range


available_units = sorted(
    df_cases["Unidad de Negocio"]
    .dropna()
    .astype(str)
    .unique()
)

selected_units = st.sidebar.multiselect(
    label="Unidad de negocio",
    options=available_units,
    default=available_units,
)


available_case_types = sorted(
    df_cases["Tipo de caso PC"]
    .dropna()
    .astype(str)
    .unique()
)

selected_case_types = st.sidebar.multiselect(
    label="Tipo de caso",
    options=available_case_types,
    default=available_case_types,
)


selected_responsibles = []

if "Resuelto por" in df_cases.columns:

    available_responsibles = sorted(
        df_cases["Resuelto por"]
        .dropna()
        .astype(str)
        .unique()
    )

    selected_responsibles = st.sidebar.multiselect(
        label="Resuelto por",
        options=available_responsibles,
        default=available_responsibles,
    )


filtered_data = apply_filters(
    df=df_cases,
    start_date=start_date,
    end_date=end_date,
    selected_units=selected_units,
    selected_types=selected_case_types,
    selected_responsibles=selected_responsibles,
)


if filtered_data.empty:
    st.warning(
        "No existen registros para la combinación "
        "de filtros seleccionada."
    )

    st.stop()


# ============================================================
# CÁLCULO DE MÉTRICAS
# ============================================================

kpis = calculate_general_kpis(filtered_data)

weekly_report = create_weekly_report(
    filtered_data
)

case_type_report = create_case_type_report(
    filtered_data
)

user_performance_report = (
    create_user_performance_report(
        filtered_data
    )
)

# ============================================================
# KPIs EJECUTIVOS
# ============================================================

st.subheader("Resumen ejecutivo")

metric_row_1 = st.columns(5)

metric_row_1[0].metric(
    label="Casos atendidos",
    value=f"{kpis['total_cases']:,}",
)

metric_row_1[1].metric(
    label="Tiempo promedio en VSC",
    value=f"{kpis['average_time'] * 60:.1f} min",
)

metric_row_1[2].metric(
    label="Mediana en VSC",
    value=f"{kpis['median_time'] * 60:.1f} min",
)

metric_row_1[3].metric(
    label="Casos ≤ 30 min",
    value=f"{kpis['pct_30_min']:.1f}%",
)

metric_row_1[4].metric(
    label="Casos 31-60 min",
    value=f"{kpis['pct_30_60_min']:.1f}%",
)


metric_row_2 = st.columns(4)

metric_row_2[0].metric(
    label="Casos > 60 min",
    value=f"{kpis['pct_over_60_min']:.1f}%",
)

metric_row_2[1].metric(
    label="Tiempo promedio en Facturación",
    value=f"{kpis['average_wait'] * 60:.1f} min",
)

metric_row_2[2].metric(
    label="Horas consumidas",
    value=f"{kpis['hours_consumed']:.1f} h",
)

metric_row_2[3].metric(
    label="Utilización de capacidad",
    value=f"{kpis['capacity_utilization']:.1f}%",
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
    detail_tab,
) = st.tabs(
    [
        "Resumen",
        "SLA y tiempos",
        "Capacidad",
        "Tipos de caso",
        "Performance del personal",
        "Detalle",
    ]
)


# ============================================================
# TAB 1: RESUMEN
# ============================================================

with summary_tab:

    chart_column_1, chart_column_2 = st.columns(2)

    with chart_column_1:

        weekly_volume_chart = (
            create_weekly_volume_chart(
                filtered_data
            )
        )

        st.plotly_chart(
            weekly_volume_chart,
            use_container_width=True,
        )

    with chart_column_2:

        sla_distribution_chart = (
            create_sla_distribution_chart(
                filtered_data
            )
        )

        st.plotly_chart(
            sla_distribution_chart,
            use_container_width=True,
        )


# ============================================================
# TAB 2: SLA Y TIEMPOS
# ============================================================

with sla_tab:

    st.subheader(
        "Cumplimiento de SLA por semana"
    )

    sla_weekly_table = weekly_report[
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
        ]
    ].copy()

    st.dataframe(
        sla_weekly_table,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(
        "Casos con mayor tiempo de atención"
    )

    detail_columns = [
        column
        for column in [
            "Fecha de apertura",
            "Unidad de Negocio",
            "Tipo de caso PC",
            "Resuelto por",
            "Tiempo en VSC (Hrs)",
            "Tiempo en Facturación (Hrs)",
            "Tiempo total caso (Hrs)",
            "Rango SLA",
        ]
        if column in filtered_data.columns
    ]

    longest_cases = (
        filtered_data[
            detail_columns
        ]
        .sort_values(
            "Tiempo en VSC (Hrs)",
            ascending=False,
        )
        .head(15)
    )

    st.dataframe(
        longest_cases,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 3: CAPACIDAD
# ============================================================

with capacity_tab:

    capacity_chart = create_capacity_chart(
        weekly_report
    )

    st.plotly_chart(
        capacity_chart,
        use_container_width=True,
    )

    st.subheader(
        "Reporte semanal de capacidad"
    )

    st.dataframe(
        weekly_report,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 4: TIPOS DE CASO
# ============================================================

with case_type_tab:

    st.subheader(
        "Desempeño por tipo de caso"
    )

    st.dataframe(
        case_type_report,
        use_container_width=True,
        hide_index=True,
    )

    st.subheader(
        "Tipos de caso con mayor volumen"
    )

    top_case_types = (
        case_type_report
        .sort_values(
            "Casos",
            ascending=False,
        )
        .head(10)
    )

    st.bar_chart(
        data=top_case_types,
        x="Tipo de caso PC",
        y="Casos",
    )

    st.subheader(
        "Tipos de caso con mayor porcentaje "
        "de casos mayores a una hora"
    )

    minimum_cases = st.slider(
        label=(
            "Mínimo de casos por tipo "
            "para incluirlo en la comparación"
        ),
        min_value=1,
        max_value=max(
            1,
            int(
                case_type_report["Casos"].max()
            ),
        ),
        value=min(
            5,
            max(
                1,
                int(
                    case_type_report[
                        "Casos"
                    ].max()
                ),
            ),
        ),
    )

    case_types_over_one_hour = (
        case_type_report[
            case_type_report["Casos"]
            >= minimum_cases
        ]
        .sort_values(
            "Pct_mayores_60_min",
            ascending=False,
        )
    )

    st.dataframe(
        case_types_over_one_hour,
        use_container_width=True,
        hide_index=True,
    )


# ============================================================
# TAB 5: PERFORMANCE DEL PERSONAL
# ============================================================

with personnel_tab:

    # ============================================================
    # TAB 5: PERFORMANCE DEL PERSONAL
    # ============================================================

    st.subheader("Performance del personal")

    st.caption(
        "Comparación del volumen de casos, tiempos en VSC "
        "y distribución de rangos de atención por usuario "
        "registrado en la columna 'Resuelto por'."
    )

    if user_performance_report.empty:

        st.info(
            "No existen registros válidos en la columna "
            "'Resuelto por' para los filtros seleccionados."
        )

    else:

        # ----------------------------------------------------
        # GRÁFICAS DE VOLUMEN Y HORAS CONSUMIDAS
        # ----------------------------------------------------

        chart_col_1, chart_col_2 = st.columns(2)

        volumen_personal = (
            user_performance_report
            .sort_values(
                "Casos",
                ascending=True,
            )
        )

        fig_volumen_personal = px.bar(
            volumen_personal,
            x="Casos",
            y="Resuelto por",
            orientation="h",
            text="Casos",
            title="Casos resueltos por persona",
        )

        fig_volumen_personal.update_traces(
            textposition="outside",
        )

        fig_volumen_personal.update_layout(
            xaxis_title="Número de casos",
            yaxis_title="Personal",
            showlegend=False,
        )

        chart_col_1.plotly_chart(
            fig_volumen_personal,
            use_container_width=True,
        )

        horas_personal = (
            user_performance_report
            .sort_values(
                "Horas_consumidas",
                ascending=True,
            )
        )

        fig_horas_personal = px.bar(
            horas_personal,
            x="Horas_consumidas",
            y="Resuelto por",
            orientation="h",
            text="Horas_consumidas",
            title="Horas acumuladas en VSC por persona",
        )

        fig_horas_personal.update_traces(
            texttemplate="%{text:.1f} h",
            textposition="outside",
        )

        fig_horas_personal.update_layout(
            xaxis_title="Horas acumuladas en VSC",
            yaxis_title="Personal",
            showlegend=False,
        )

        chart_col_2.plotly_chart(
            fig_horas_personal,
            use_container_width=True,
        )

        # ----------------------------------------------------
        # DISTRIBUCIÓN DE TIEMPOS POR PERSONA
        # ----------------------------------------------------

        st.subheader(
            "Distribución de tiempos por persona"
        )

        maximo_casos_persona = max(
            1,
            int(
                user_performance_report[
                    "Casos"
                ].max()
            ),
        )

        valor_inicial = min(
            1,
            maximo_casos_persona,
        )

        minimo_casos_persona = st.slider(
            label=(
                "Mínimo de casos para incluir a la persona "
                "en la comparación"
            ),
            min_value=1,
            max_value=maximo_casos_persona,
            value=valor_inicial,
            key="minimo_casos_persona",
        )

        reporte_personal_comparable = (
            user_performance_report[
                user_performance_report["Casos"]
                >= minimo_casos_persona
            ]
            .copy()
            .sort_values(
                "Pct_hasta_30_min",
                ascending=True,
            )
        )

        if reporte_personal_comparable.empty:

            st.info(
                "No existen personas con el número mínimo "
                "de casos seleccionado."
            )

        else:

            fig_sla_personal = go.Figure()

            fig_sla_personal.add_trace(
                go.Bar(
                    y=reporte_personal_comparable[
                        "Resuelto por"
                    ],
                    x=reporte_personal_comparable[
                        "Pct_hasta_30_min"
                    ],
                    name="Hasta 30 min",
                    orientation="h",
                    text=(
                        reporte_personal_comparable[
                            "Pct_hasta_30_min"
                        ]
                        .round(1)
                        .astype(str)
                        + "%"
                    ),
                )
            )

            fig_sla_personal.add_trace(
                go.Bar(
                    y=reporte_personal_comparable[
                        "Resuelto por"
                    ],
                    x=reporte_personal_comparable[
                        "Pct_30_a_60_min"
                    ],
                    name="31 a 60 min",
                    orientation="h",
                    text=(
                        reporte_personal_comparable[
                            "Pct_30_a_60_min"
                        ]
                        .round(1)
                        .astype(str)
                        + "%"
                    ),
                )
            )

            fig_sla_personal.add_trace(
                go.Bar(
                    y=reporte_personal_comparable[
                        "Resuelto por"
                    ],
                    x=reporte_personal_comparable[
                        "Pct_mayores_60_min"
                    ],
                    name="Más de 60 min",
                    orientation="h",
                    text=(
                        reporte_personal_comparable[
                            "Pct_mayores_60_min"
                        ]
                        .round(1)
                        .astype(str)
                        + "%"
                    ),
                )
            )

            fig_sla_personal.update_layout(
                title=(
                    "Distribución porcentual del tiempo en VSC"
                ),
                xaxis_title="Porcentaje de casos",
                yaxis_title="Personal",
                barmode="stack",
                xaxis_range=[0, 100],
                legend_title="Rango de atención",
            )

            fig_sla_personal.update_traces(
                textposition="inside",
            )

            st.plotly_chart(
                fig_sla_personal,
                use_container_width=True,
            )

        # ----------------------------------------------------
        # TABLA RESUMIDA
        # ----------------------------------------------------

        st.subheader("Resumen de performance")

        resumen_personal = (
            user_performance_report[
                [
                    "Resuelto por",
                    "Casos",
                    "Horas_consumidas",
                    "Tiempo_promedio_VSC",
                    "Mediana_VSC",
                    "Pct_hasta_30_min",
                    "Pct_30_a_60_min",
                    "Pct_mayores_60_min",
                ]
            ]
            .copy()
        )

        resumen_personal[
            "Promedio VSC (min)"
        ] = (
            resumen_personal[
                "Tiempo_promedio_VSC"
            ]
            * 60
        ).round(1)

        resumen_personal[
            "Mediana VSC (min)"
        ] = (
            resumen_personal[
                "Mediana_VSC"
            ]
            * 60
        ).round(1)

        resumen_personal = resumen_personal.rename(
            columns={
                "Resuelto por": "Personal",
                "Horas_consumidas": "Horas en VSC",
                "Pct_hasta_30_min": "% hasta 30 min",
                "Pct_30_a_60_min": "% 31 a 60 min",
                "Pct_mayores_60_min": "% más de 60 min",
            }
        )

        resumen_personal = resumen_personal[
            [
                "Personal",
                "Casos",
                "Promedio VSC (min)",
                "Mediana VSC (min)",
                "% hasta 30 min",
                "% 31 a 60 min",
                "% más de 60 min",
                "Horas en VSC",
            ]
        ]

        st.dataframe(
            resumen_personal,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Casos": st.column_config.NumberColumn(
                    "Casos",
                    format="%d",
                ),
                "Promedio VSC (min)": (
                    st.column_config.NumberColumn(
                        "Promedio VSC (min)",
                        format="%.1f min",
                    )
                ),
                "Mediana VSC (min)": (
                    st.column_config.NumberColumn(
                        "Mediana VSC (min)",
                        format="%.1f min",
                    )
                ),
                "% hasta 30 min": (
                    st.column_config.ProgressColumn(
                        "% hasta 30 min",
                        min_value=0,
                        max_value=100,
                        format="%.1f%%",
                    )
                ),
                "% 31 a 60 min": (
                    st.column_config.NumberColumn(
                        "% 31 a 60 min",
                        format="%.1f%%",
                    )
                ),
                "% más de 60 min": (
                    st.column_config.NumberColumn(
                        "% más de 60 min",
                        format="%.1f%%",
                    )
                ),
                "Horas en VSC": (
                    st.column_config.NumberColumn(
                        "Horas en VSC",
                        format="%.2f h",
                    )
                ),
            },
        )

        # ----------------------------------------------------
        # ANÁLISIS INDIVIDUAL
        # ----------------------------------------------------

        st.subheader("Análisis individual")

        usuario_seleccionado = st.selectbox(
            label="Seleccionar personal",
            options=sorted(
                user_performance_report[
                    "Resuelto por"
                ].unique()
            ),
            key="usuario_performance",
        )

        datos_usuario = (
            user_performance_report[
                user_performance_report[
                    "Resuelto por"
                ]
                == usuario_seleccionado
            ]
            .iloc[0]
        )

        indicadores_usuario = st.columns(5)

        indicadores_usuario[0].metric(
            label="Casos resueltos",
            value=int(
                datos_usuario["Casos"]
            ),
        )

        indicadores_usuario[1].metric(
            label="Promedio en VSC",
            value=(
                f"{datos_usuario['Tiempo_promedio_VSC'] * 60:.1f} min"
            ),
        )

        indicadores_usuario[2].metric(
            label="Mediana en VSC",
            value=(
                f"{datos_usuario['Mediana_VSC'] * 60:.1f} min"
            ),
        )

        indicadores_usuario[3].metric(
            label="Hasta 30 min",
            value=(
                f"{datos_usuario['Pct_hasta_30_min']:.1f}%"
            ),
        )

        indicadores_usuario[4].metric(
            label="Más de 60 min",
            value=(
                f"{datos_usuario['Pct_mayores_60_min']:.1f}%"
            ),
        )

        casos_usuario = filtered_data[
            filtered_data[
                "Resuelto por"
            ].astype(str)
            == str(usuario_seleccionado)
        ].copy()

        columnas_usuario = [
            column
            for column in [
                "Fecha de apertura",
                "Unidad de Negocio",
                "Tipo de caso PC",
                "Tiempo en VSC (Hrs)",
                "Tiempo en Facturación (Hrs)",
                "Tiempo total caso (Hrs)",
                "Rango SLA",
            ]
            if column in casos_usuario.columns
        ]

        st.dataframe(
            casos_usuario[
                columnas_usuario
            ]
            .sort_values(
                "Tiempo en VSC (Hrs)",
                ascending=False,
            ),
            use_container_width=True,
            hide_index=True,
        )

# ============================================================
# TAB 6: DETALLE
# ============================================================

with detail_tab:

    st.subheader(
        "Detalle de casos filtrados"
    )

    detail_columns = [
        column
        for column in [
            "Fecha de apertura",
            "Unidad de Negocio",
            "Tipo de caso PC",
            "Resuelto por",
            "Tiempo en VSC (Hrs)",
            "Tiempo en Facturación (Hrs)",
            "Tiempo total caso (Hrs)",
            "Semana",
            "Día semana",
            "Rango SLA",
        ]
        if column in filtered_data.columns
    ]

    detail_data = (
        filtered_data[
            detail_columns
        ]
        .sort_values(
            "Fecha de apertura",
            ascending=False,
        )
    )

    st.dataframe(
        detail_data,
        use_container_width=True,
        hide_index=True,
    )

    excel_report = create_excel_download(
        filtered_data=filtered_data,
        weekly_report=weekly_report,
        case_type_report=case_type_report,
        user_performance_report=user_performance_report,
    )

    st.download_button(
        label="Descargar reporte filtrado en Excel",
        data=excel_report,
        file_name=(
            "planning_services_dashboard.xlsx"
        ),
        mime=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )


# ============================================================
# PIE DE PÁGINA
# ============================================================

st.markdown(
    """
    <div class="footer">
        Planning Services Executive Dashboard · Versión 1.0
    </div>
    """,
    unsafe_allow_html=True,
)
