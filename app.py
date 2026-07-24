import streamlit as st

from src.charts import (
    create_capacity_chart,
    create_sla_distribution_chart,
    create_weekly_volume_chart,
)
from src.data_loader import load_cases_data
from src.metrics import (
    calculate_general_kpis,
    create_case_type_report,
    create_weekly_report,
)
from src.preprocessing import prepare_cases_data


st.set_page_config(
    page_title="Planning Services Dashboard",
    page_icon="📊",
    layout="wide",
)


@st.cache_data
def get_data():
    raw_data = load_cases_data()
    return prepare_cases_data(raw_data)


df_cases = get_data()


st.title("Planning Services Executive Dashboard")

st.caption(
    "Análisis ejecutivo del volumen, tiempos de atención, "
    "cumplimiento de SLA y utilización de capacidad."
)


# FILTROS

st.sidebar.header("Filtros")

business_units = sorted(
    df_cases["Unidad de Negocio"]
    .dropna()
    .astype(str)
    .unique()
)

case_types = sorted(
    df_cases["Tipo de caso PC"]
    .dropna()
    .astype(str)
    .unique()
)

selected_units = st.sidebar.multiselect(
    "Unidad de negocio",
    options=business_units,
    default=business_units,
)

selected_types = st.sidebar.multiselect(
    "Tipo de caso",
    options=case_types,
    default=case_types,
)


filtered_data = df_cases[
    df_cases["Unidad de Negocio"]
    .astype(str)
    .isin(selected_units)
    & df_cases["Tipo de caso PC"]
    .astype(str)
    .isin(selected_types)
].copy()


if filtered_data.empty:
    st.warning(
        "No existen registros para los filtros seleccionados."
    )
    st.stop()


# MÉTRICAS

kpis = calculate_general_kpis(filtered_data)
weekly_report = create_weekly_report(filtered_data)
case_type_report = create_case_type_report(filtered_data)


metric_columns = st.columns(5)

metric_columns[0].metric(
    "Casos",
    f"{kpis['total_cases']:,}",
)

metric_columns[1].metric(
    "Promedio",
    f"{kpis['average_time'] * 60:.1f} min",
)

metric_columns[2].metric(
    "SLA ≤ 30 min",
    f"{kpis['sla_30']:.1f}%",
)

metric_columns[3].metric(
    "SLA ≤ 1 hora",
    f"{kpis['sla_1_hour']:.1f}%",
)

metric_columns[4].metric(
    "Utilización",
    f"{kpis['capacity_utilization']:.1f}%",
)


# GRÁFICAS

chart_column_1, chart_column_2 = st.columns(2)

with chart_column_1:
    st.plotly_chart(
        create_weekly_volume_chart(filtered_data),
        use_container_width=True,
    )

with chart_column_2:
    st.plotly_chart(
        create_sla_distribution_chart(filtered_data),
        use_container_width=True,
    )


st.plotly_chart(
    create_capacity_chart(weekly_report),
    use_container_width=True,
)


# TABLAS

tab_weekly, tab_cases, tab_detail = st.tabs(
    [
        "Reporte semanal",
        "Tipos de caso",
        "Detalle",
    ]
)

with tab_weekly:
    st.dataframe(
        weekly_report,
        use_container_width=True,
        hide_index=True,
    )

with tab_cases:
    st.dataframe(
        case_type_report,
        use_container_width=True,
        hide_index=True,
    )

with tab_detail:
    st.dataframe(
        filtered_data,
        use_container_width=True,
        hide_index=True,
    )
