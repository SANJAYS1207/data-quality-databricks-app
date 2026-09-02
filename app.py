import streamlit as st
import pandas as pd

from services.gx_service import (
    EXPECTATION_CATEGORIES,
    describe_rule,
    get_expectation_schema,
    list_expectations_by_category,
    parse_list_value,
    parse_raw_value,
    rule_scope_key,
    run_data_quality_checks,
    search_expectations,
)
from services.databricks_service import load_databricks_table


# ============================================================
# Dynamic Parameter Widget
# ============================================================

def _render_param(spec, editing_kwargs, selected_expectation, form_key):

    name = spec["name"]
    widget = spec["widget"]
    label = name.replace("_", " ").capitalize()
    default = editing_kwargs.get(name)
    key = f"param_{form_key}_{selected_expectation}_{name}"

    if widget == "bool":

        return st.checkbox(
            label,
            value=bool(default) if default is not None else False,
            key=key
        )

    if widget == "number":

        return st.number_input(
            label,
            value=(
                float(default)
                if isinstance(default, (int, float))
                else 0.0
            ),
            key=key
        )

    if widget == "list":

        text_default = (
            ", ".join(str(v) for v in default)
            if isinstance(default, list)
            else ""
        )

        text = st.text_input(
            label,
            value=text_default,
            placeholder="Example: Active, Inactive",
            key=key
        )

        return parse_list_value(text) if text else []

    if widget == "text":

        return st.text_input(
            label,
            value=str(default) if default is not None else "",
            key=key
        )

    text = st.text_area(
        label,
        value=repr(default) if default is not None else "",
        help="Enter a Python/JSON literal (e.g. a dict or list).",
        key=key
    )

    return parse_raw_value(text) if text else None


# ============================================================
# Rule Table Action Handler (Edit / Delete)
# ============================================================

def _handle_rule_action():

    click = st.session_state.get("rule_table_action")

    if not click or click.row is None:
        return

    row = click.row

    if row >= len(st.session_state.selected_rules):
        return

    if "Delete" in click.label:

        st.session_state.selected_rules.pop(row)

        if st.session_state.editing_index == row:

            st.session_state.editing_index = None

        elif (
            st.session_state.editing_index is not None
            and st.session_state.editing_index > row
        ):

            st.session_state.editing_index -= 1

    elif "Edit" in click.label:

        st.session_state.editing_index = row


# ============================================================
# Page Configuration
# ============================================================

st.set_page_config(
    page_title="Data Quality Dashboard",
    page_icon=":material/monitoring:",
    layout="wide"
)


# ============================================================
# Page Title
# ============================================================

st.title(":material/monitoring: Data quality dashboard")

st.caption(
    "Build data quality rules from any Great Expectations "
    "expectation and validate your data against them."
)


# ============================================================
# Initialize Rule Storage
# ============================================================

if "selected_rules" not in st.session_state:
    st.session_state.selected_rules = []

# Drop any rules saved under the old (pre-dynamic-expectations) rule
# format from a still-open browser session, so a stale session_state
# doesn't crash the app after an update.
st.session_state.selected_rules = [
    rule for rule in st.session_state.selected_rules
    if "expectation_type" in rule and "kwargs" in rule
]

if "editing_index" not in st.session_state:
    st.session_state.editing_index = None

if (
    st.session_state.editing_index is not None
    and st.session_state.editing_index >= len(st.session_state.selected_rules)
):
    st.session_state.editing_index = None

if "dq_data" not in st.session_state:
    st.session_state.dq_data = None


# ============================================================
# Databricks Data Loading
# ============================================================

try:
    with st.spinner("Loading data from Unity Catalog..."):
        df = load_databricks_table()
    data_loaded = True
except Exception as e:
    st.error(f"Failed to load data from Databricks: {e}")
    data_loaded = False


if data_loaded:

    # ========================================================
    # Data Information
    # ========================================================

    st.success("Data loaded successfully from Unity Catalog", icon=":material/check_circle:")

    st.caption(
        f"customer_dq · {len(df):,} rows · "
        f"{len(df.columns)} columns"
    )


    # ========================================================
    # Data Preview
    # ========================================================

    with st.container(border=True):

        st.subheader(":material/visibility: Data preview")

        st.dataframe(df)


    # ========================================================
    # Rule Configuration
    # ========================================================

    with st.container(border=True):

        st.subheader(":material/tune: Configure data quality rules")


        # --------------------------------------------------------
        # Editing State
        # --------------------------------------------------------

        editing_index = st.session_state.editing_index

        editing_rule = (
            st.session_state.selected_rules[editing_index]
            if editing_index is not None
            else None
        )

        editing_schema = (
            get_expectation_schema(editing_rule["expectation_type"])
            if editing_rule
            else None
        )

        if editing_rule:

            st.info(
                f"Editing rule {editing_index + 1}",
                icon=":material/edit:"
            )

        # A Streamlit widget with no `key` (or an unchanging one) keeps
        # its previous value on rerun and ignores `index=`/`value=`
        # after the first render. Scoping every form widget's key to
        # the rule currently being edited forces a fresh widget - and
        # therefore our computed default - whenever the edit target
        # changes (including switching from "add" to "edit").
        form_key = f"edit{editing_index}" if editing_index is not None else "new"


        # --------------------------------------------------------
        # Select Column
        # --------------------------------------------------------

        columns_list = list(df.columns)

        column = st.selectbox(
            "Select column",
            columns_list,
            index=(
                columns_list.index(editing_rule["kwargs"]["column"])
                if editing_rule and "column" in editing_rule["kwargs"]
                else 0
            ),
            key=f"column_select_{form_key}"
        )


        # --------------------------------------------------------
        # Category / Search
        # --------------------------------------------------------

        filter_col1, filter_col2 = st.columns(2)

        with filter_col1:

            category = st.selectbox(
                "Category",
                EXPECTATION_CATEGORIES,
                index=(
                    EXPECTATION_CATEGORIES.index(
                        editing_schema["categories"][0]
                    )
                    if editing_schema
                    else 0
                ),
                help=(
                    "Categories are a UI grouping curated for this app "
                    "(Great Expectations itself has no categories). "
                    "⭐ Recommended is a hand-picked set of the most "
                    "commonly used checks: not-null, unique, range, "
                    "set membership, regex match, type check, row "
                    "count, and column-set match."
                ),
                key=f"category_select_{form_key}"
            )

        with filter_col2:

            search_query = st.text_input(
                "Search expectations",
                placeholder="Search...",
                icon=":material/search:",
                key=f"search_{form_key}"
            )


        # --------------------------------------------------------
        # Available Expectations
        # --------------------------------------------------------

        expectation_names = (
            search_expectations(search_query)
            if search_query
            else list_expectations_by_category(category)
        )

        if not expectation_names:

            st.warning(
                "No expectations match this filter.",
                icon=":material/search_off:"
            )

            selected_expectation = None

        else:

            selected_expectation = st.selectbox(
                "Available expectations",
                expectation_names,
                index=(
                    expectation_names.index(editing_rule["expectation_type"])
                    if editing_rule
                    and editing_rule["expectation_type"] in expectation_names
                    else 0
                ),
                key=f"expectation_select_{form_key}"
            )


        # ========================================================
        # Dynamic Expectation Form
        # ========================================================

        selected_rule = None

        if selected_expectation:

            schema = get_expectation_schema(selected_expectation)

            st.markdown(f"**{selected_expectation}**")

            if schema["doc"]:

                st.caption(schema["doc"])

            editing_kwargs = (
                editing_rule["kwargs"]
                if editing_rule
                and editing_rule["expectation_type"] == selected_expectation
                else {}
            )

            kwargs = {}


            # ----------------------------------------------------
            # Column Binding
            # ----------------------------------------------------

            if schema["column_mode"] == "single":

                kwargs["column"] = column

            elif schema["column_mode"] == "pair":

                pair_col1, pair_col2 = st.columns(2)

                with pair_col1:

                    default_a = editing_kwargs.get("column_A", column)

                    column_a = st.selectbox(
                        "Column A",
                        columns_list,
                        index=(
                            columns_list.index(default_a)
                            if default_a in columns_list
                            else 0
                        ),
                        key=f"param_column_A_{form_key}_{selected_expectation}"
                    )

                with pair_col2:

                    default_b = editing_kwargs.get("column_B")

                    column_b = st.selectbox(
                        "Column B",
                        columns_list,
                        index=(
                            columns_list.index(default_b)
                            if default_b in columns_list
                            else min(1, len(columns_list) - 1)
                        ),
                        key=f"param_column_B_{form_key}_{selected_expectation}"
                    )

                kwargs["column_A"] = column_a
                kwargs["column_B"] = column_b

            elif schema["column_mode"] == "multi":

                multi_field = schema["multi_field"]

                default_columns = [
                    c for c in editing_kwargs.get(multi_field, [column])
                    if c in columns_list
                ] or [column]

                selected_columns = st.multiselect(
                    "Select columns",
                    columns_list,
                    default=default_columns,
                    key=f"param_column_list_{form_key}_{selected_expectation}"
                )

                kwargs[multi_field] = selected_columns

                if schema["needs_column_and_multi"]:

                    kwargs["column"] = (
                        selected_columns[0] if selected_columns else column
                    )

            else:

                st.caption(
                    ":material/info: This is a table-level expectation "
                    "- the column selected above is not used."
                )


            # ----------------------------------------------------
            # Primary Parameters
            # ----------------------------------------------------

            missing_required = []

            for spec in schema["primary_params"]:

                value = _render_param(
                    spec,
                    editing_kwargs,
                    selected_expectation,
                    form_key
                )

                kwargs[spec["name"]] = value

                if spec["widget"] in ("text", "list") and not value:

                    missing_required.append(spec["name"])

                if spec["widget"] == "raw" and value is None:

                    missing_required.append(spec["name"])


            # ----------------------------------------------------
            # Advanced Parameters
            # ----------------------------------------------------

            if schema["advanced_params"]:

                with st.expander(
                    "Advanced options",
                    icon=":material/settings:"
                ):

                    for spec in schema["advanced_params"]:

                        value = _render_param(
                            spec,
                            editing_kwargs,
                            selected_expectation,
                            form_key
                        )

                        is_empty = (
                            value in (None, "", [])
                            if spec["widget"] in ("text", "list", "raw")
                            else False
                        )

                        if not is_empty:

                            kwargs[spec["name"]] = value


            selected_rule = {
                "expectation_type": selected_expectation,
                "kwargs": kwargs
            }


        # ========================================================
        # Add Rule Button
        # ========================================================

        with st.container(horizontal=True):

            add_clicked = st.button(
                "Save changes" if editing_rule else "Add rule",
                icon=":material/save:" if editing_rule else ":material/add:",
                type="primary",
                disabled=selected_rule is None
            )

            cancel_clicked = (
                st.button("Cancel", icon=":material/close:")
                if editing_rule
                else False
            )

        if cancel_clicked:

            st.session_state.editing_index = None

            st.rerun()


        if add_clicked and selected_rule:

            is_duplicate = any(
                existing_rule["expectation_type"]
                == selected_rule["expectation_type"]
                and rule_scope_key(existing_rule["kwargs"])
                == rule_scope_key(selected_rule["kwargs"])
                for existing_index, existing_rule in enumerate(
                    st.session_state.selected_rules
                )
                if existing_index != editing_index
            )

            if missing_required:

                st.warning(
                    "Please fill in: " + ", ".join(missing_required),
                    icon=":material/warning:"
                )

            elif is_duplicate:

                st.warning(
                    f"A '{selected_expectation}' rule already exists "
                    "for this column. Edit the existing rule instead "
                    "of adding it again.",
                    icon=":material/warning:"
                )

            elif editing_rule:

                st.session_state.selected_rules[editing_index] = (
                    selected_rule
                )

                st.session_state.editing_index = None

                st.success(
                    "Rule updated successfully",
                    icon=":material/check_circle:"
                )

            else:

                st.session_state.selected_rules.append(
                    selected_rule
                )

                st.success(
                    "Rule added successfully",
                    icon=":material/check_circle:"
                )


    # ========================================================
    # Display Stored Rules (always visible)
    # ========================================================

    with st.container(border=True):

        st.subheader(":material/checklist: Configured rules")

        if st.session_state.selected_rules:

            rules_view_df = pd.DataFrame({
                "rule": [
                    describe_rule(rule["expectation_type"], rule["kwargs"])
                    for rule in st.session_state.selected_rules
                ],
                "category": [
                    get_expectation_schema(rule["expectation_type"])
                    ["categories"][0]
                    for rule in st.session_state.selected_rules
                ],
                "actions": [
                    [":material/edit: Edit", ":material/delete: Delete"]
                    for _ in st.session_state.selected_rules
                ],
            })

            st.dataframe(
                rules_view_df,
                hide_index=True,
                column_config={
                    "rule": st.column_config.TextColumn(
                        "Rule", width="large"
                    ),
                    "category": st.column_config.TextColumn(
                        "Category", width="small"
                    ),
                    "actions": st.column_config.ButtonColumn(
                        "Actions",
                        on_click=_handle_rule_action,
                        key="rule_table_action"
                    ),
                }
            )

            if st.button(
                "Clear all rules",
                icon=":material/delete_sweep:"
            ):

                st.session_state.selected_rules = []

                st.rerun()

        else:

            st.info(
                "No rules configured yet. Select a column and an "
                "expectation above, then click Add rule.",
                icon=":material/info:"
            )


    # ========================================================
    # Run All Rules
    # ========================================================

    if st.button(
        "Run all data quality checks",
        icon=":material/play_arrow:",
        type="primary"
    ):

        if not st.session_state.selected_rules:

            st.warning(
                "Please add at least one rule before running.",
                icon=":material/warning:"
            )

        else:

            with st.spinner(
                "Running Great Expectations validation..."
            ):

                st.session_state.dq_data = run_data_quality_checks(
                    df,
                    st.session_state.selected_rules
                )


    # ========================================================
    # Display Data Quality Results
    # ========================================================

    if st.session_state.dq_data:

        dq_data = st.session_state.dq_data

        summary = dq_data["summary"]

        rules = dq_data["rules"]

        dq_score = summary["dq_score"]


        # ====================================================
        # Overall Status
        # ====================================================

        if dq_score >= 90:

            st.success(
                "Excellent data quality",
                icon=":material/check_circle:"
            )

        elif dq_score >= 70:

            st.warning(
                "Moderate data quality",
                icon=":material/warning:"
            )

        else:

            st.error(
                "Poor data quality",
                icon=":material/error:"
            )


        # ====================================================
        # Summary Metrics
        # ====================================================

        st.subheader(":material/analytics: Data quality summary")

        with st.container(horizontal=True):

            st.metric(
                "DQ score",
                f"{summary['dq_score']:.1f}%",
                border=True
            )

            st.metric(
                "Total rules",
                summary["total_rules"],
                border=True
            )

            st.metric(
                "Passed",
                summary["passed"],
                border=True
            )

            st.metric(
                "Failed",
                summary["failed"],
                border=True
            )


        # ====================================================
        # Rule Results
        # ====================================================

        with st.container(border=True):

            st.subheader(":material/table_chart: Rule results")

            results_df = pd.DataFrame(
                rules
            )

            styled_results = results_df.style.map(
                lambda v: (
                    "background-color: rgba(16, 185, 129, 0.18)"
                    if v == "PASS"
                    else "background-color: rgba(239, 68, 68, 0.18)"
                ),
                subset=["status"]
            )

            st.dataframe(
                styled_results,
                hide_index=True,
                column_config={
                    "rule": st.column_config.TextColumn(
                        "Rule", width="large"
                    ),
                    "status": st.column_config.TextColumn("Status"),
                    "checked": st.column_config.NumberColumn("Checked"),
                    "failed": st.column_config.NumberColumn("Failed"),
                    "failure_percent": st.column_config.NumberColumn(
                        "Failure %", format="%.1f%%"
                    ),
                }
            )


        # ====================================================
        # Rule Status Chart
        # ====================================================

        chart_col1, chart_col2 = st.columns(2)

        with chart_col1:

            with st.container(border=True):

                st.subheader(":material/bar_chart: Rule status overview")

                status_counts = results_df["status"].value_counts()

                st.bar_chart(status_counts)


        # ====================================================
        # Failure Percentage Chart
        # ====================================================

        with chart_col2:

            with st.container(border=True):

                st.subheader(":material/trending_down: Failure % by rule")

                failure_chart_df = (
                    results_df[
                        ["rule", "failure_percent"]
                    ]
                    .set_index("rule")
                )

                st.bar_chart(failure_chart_df)
