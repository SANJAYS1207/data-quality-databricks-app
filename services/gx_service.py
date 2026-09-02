import ast
import re

import great_expectations as gx
import great_expectations.expectations as gxe


# ============================================================
# Expectation Catalog
# ============================================================
#
# The list of Expectation classes below is NOT hard-coded - it is
# discovered from whatever `great_expectations.expectations`
# actually ships in the installed package version, so the catalog
# always matches what's really available at runtime.
#
# The "category" groupings, however, are a curated UI convenience.
# Great Expectations itself has no notion of categories - these
# exist purely to make the (currently ~58) expectations easier to
# browse from the app.

CATEGORY_ORDER = [
    "⭐ Recommended",
    "Completeness",
    "Uniqueness",
    "Numeric",
    "Text & Pattern",
    "Set / Values",
    "Date & Time",
    "Table / Schema",
    "Multi-column",
    "Advanced",
]

_DEFAULT_CATEGORY = "Advanced"

_CATEGORY_MEMBERS = {
    "⭐ Recommended": {
        "ExpectColumnValuesToNotBeNull",
        "ExpectColumnValuesToBeUnique",
        "ExpectColumnValuesToBeBetween",
        "ExpectColumnValuesToBeInSet",
        "ExpectColumnValuesToMatchRegex",
        "ExpectColumnValuesToBeOfType",
        "ExpectTableRowCountToBeBetween",
        "ExpectTableColumnsToMatchSet",
    },
    "Completeness": {
        "ExpectColumnValuesToNotBeNull",
        "ExpectColumnValuesToBeNull",
        "ExpectColumnProportionOfNonNullValuesToBeBetween",
    },
    "Uniqueness": {
        "ExpectColumnValuesToBeUnique",
        "ExpectColumnDistinctValuesToBeInSet",
        "ExpectColumnDistinctValuesToContainSet",
        "ExpectColumnDistinctValuesToEqualSet",
        "ExpectColumnProportionOfUniqueValuesToBeBetween",
        "ExpectColumnUniqueValueCountToBeBetween",
        "ExpectCompoundColumnsToBeUnique",
        "ExpectSelectColumnValuesToBeUniqueWithinRecord",
        "ExpectMulticolumnValuesToBeUnique",
    },
    "Numeric": {
        "ExpectColumnValuesToBeBetween",
        "ExpectColumnMaxToBeBetween",
        "ExpectColumnMinToBeBetween",
        "ExpectColumnMeanToBeBetween",
        "ExpectColumnMedianToBeBetween",
        "ExpectColumnStdevToBeBetween",
        "ExpectColumnSumToBeBetween",
        "ExpectColumnValueZScoresToBeLessThan",
        "ExpectColumnValuesToNotBeOutliers",
        "ExpectColumnValuesToBeIncreasing",
        "ExpectColumnValuesToBeDecreasing",
    },
    "Text & Pattern": {
        "ExpectColumnValueLengthsToBeBetween",
        "ExpectColumnValueLengthsToEqual",
        "ExpectColumnValuesToMatchRegex",
        "ExpectColumnValuesToNotMatchRegex",
        "ExpectColumnValuesToMatchRegexList",
        "ExpectColumnValuesToNotMatchRegexList",
        "ExpectColumnValuesToMatchLikePattern",
        "ExpectColumnValuesToNotMatchLikePattern",
        "ExpectColumnValuesToMatchLikePatternList",
        "ExpectColumnValuesToNotMatchLikePatternList",
        "ExpectColumnValuesToBeJsonParseable",
        "ExpectColumnValuesToMatchJsonSchema",
    },
    "Set / Values": {
        "ExpectColumnValuesToBeInSet",
        "ExpectColumnValuesToNotBeInSet",
        "ExpectColumnMostCommonValueToBeInSet",
        "ExpectColumnDistinctValuesToBeInSet",
        "ExpectColumnDistinctValuesToContainSet",
        "ExpectColumnDistinctValuesToEqualSet",
    },
    "Date & Time": {
        "ExpectColumnValuesToBeDateutilParseable",
        "ExpectColumnValuesToMatchStrftimeFormat",
    },
    "Table / Schema": {
        "ExpectColumnToExist",
        "ExpectColumnValuesToBeOfType",
        "ExpectColumnValuesToBeInTypeList",
        "ExpectTableColumnCountToBeBetween",
        "ExpectTableColumnCountToEqual",
        "ExpectTableColumnsToMatchOrderedList",
        "ExpectTableColumnsToMatchSet",
        "ExpectTableRowCountToBeBetween",
        "ExpectTableRowCountToEqual",
        "ExpectTableRowCountToEqualOtherTable",
    },
    "Multi-column": {
        "ExpectColumnPairValuesAToBeGreaterThanB",
        "ExpectColumnPairValuesToBeEqual",
        "ExpectColumnPairValuesToBeInSet",
        "ExpectCompoundColumnsToBeUnique",
        "ExpectMulticolumnSumToEqual",
        "ExpectMulticolumnValuesToBeEqual",
        "ExpectMulticolumnValuesToBeUnique",
        "ExpectSelectColumnValuesToBeUniqueWithinRecord",
    },
}

# Fields common to (almost) every Expectation - configuration/
# metadata knobs rather than the parameters that define the rule
# itself. Never shown in the dynamic form.
_EXCLUDED_FIELDS = {
    "id", "meta", "notes", "result_format", "description",
    "catch_exceptions", "rendered_content", "severity", "windows",
    "batch_id", "mostly", "row_condition", "condition_parser",
}

# Fields that identify *which column(s)* the rule applies to.
# These are rendered as column pickers, never as generic params.
_COLUMN_FIELDS = {"column", "column_A", "column_B", "column_list", "column_set"}

# Secondary tuning knobs - present on the form, but tucked away
# under "Advanced options" instead of cluttering the primary form.
_ADVANCED_FIELD_NAMES = {
    "strict_min", "strict_max", "ties_okay", "allow_relative_error",
    "match_on", "ignore_row_if", "column_index", "exact_match",
    "library_metadata", "internal_weight_holdout", "tail_weight_holdout",
    "bucketize_data", "or_equal",
}

# This app only ever registers a single in-memory dataframe as its one
# data source/asset (see run_data_quality_checks below), so expectations
# that compare against a *second* table or an arbitrary SQL query have
# no way to succeed here and are excluded from the catalog entirely.
#
# ExpectMulticolumnValuesToBeUnique is excluded separately: in this GX
# version its `expectation_type` registry key is blank, so GX itself
# cannot look up an implementation for it (verified directly against
# great_expectations.expectations.registry.get_expectation_impl).
#
# ExpectColumnQuantileValuesToBeBetween and ExpectColumnKLDivergenceTo
# BeLessThan are excluded because persisting their validation result
# always raises `TypeError: Object of type bool is not JSON
# serializable` inside GX's own results-store serializer (verified via
# full traceback) - a numpy bool leaking out of these two statistical
# metric providers, unrelated to which kwargs are supplied.
_UNSUPPORTED_EXPECTATIONS = {
    "ExpectTableRowCountToEqualOtherTable",
    "ExpectQueryResultsToMatchComparison",
    "ExpectMulticolumnValuesToBeUnique",
    "ExpectColumnQuantileValuesToBeBetween",
    "ExpectColumnKLDivergenceToBeLessThan",
}


def _friendly_label(class_name: str) -> str:
    name = class_name[len("Expect"):] if class_name.startswith("Expect") else class_name
    words = re.findall(r"[A-Z][a-z0-9]*|[A-Z]+(?![a-z])", name)
    return " ".join(words) if words else class_name


def _field_widget_kind(field) -> str:
    # pydantic's "Constrained*Value" wrapper classes (e.g.
    # ConstrainedFloatValue) run the wrapped type name straight into
    # "value" with no separator, and "constrained" itself contains
    # "str" (con-STR-ained) - strip it so the substring checks below
    # only see the actual wrapped primitive type name.
    type_str = str(field.outer_type_).lower().replace("constrained", "")

    if "tuple" in type_str:
        return "raw"

    if "bool" in type_str and "list" not in type_str:
        return "bool"

    if ("float" in type_str or "int" in type_str) and "str" not in type_str:
        return "number"

    if "list" in type_str or "sequence" in type_str:
        return "list"

    if "str" in type_str:
        return "text"

    return "raw"


def _column_mode(field_names: set) -> str:
    if "column_list" in field_names or "column_set" in field_names:
        return "multi"
    if "column_A" in field_names and "column_B" in field_names:
        return "pair"
    if "column" in field_names:
        return "single"
    return "none"


def _build_catalog() -> dict:
    catalog = {}

    for name in sorted(dir(gxe)):

        if not name.startswith("Expect") or name == "Expectation":
            continue

        if name in _UNSUPPORTED_EXPECTATIONS:
            continue

        cls = getattr(gxe, name)

        if not hasattr(cls, "__fields__"):
            continue

        field_names = set(cls.__fields__.keys())

        primary_params = []
        advanced_params = []

        for field_name, field in cls.__fields__.items():

            if field_name in _EXCLUDED_FIELDS or field_name in _COLUMN_FIELDS:
                continue

            spec = {"name": field_name, "widget": _field_widget_kind(field)}

            if field_name in _ADVANCED_FIELD_NAMES:
                advanced_params.append(spec)
            else:
                primary_params.append(spec)

        categories = sorted(
            category
            for category, members in _CATEGORY_MEMBERS.items()
            if name in members
        ) or [_DEFAULT_CATEGORY]

        catalog[name] = {
            "name": name,
            "label": _friendly_label(name),
            "doc": (cls.__doc__ or "").strip().split("\n")[0].strip(),
            "categories": categories,
            "column_mode": _column_mode(field_names),
            "multi_field": (
                "column_list" if "column_list" in field_names
                else "column_set" if "column_set" in field_names
                else None
            ),
            # A handful of multi-column expectations (e.g.
            # ExpectMulticolumnValuesToBeUnique) require *both* a
            # `column_list` and a standalone `column` field.
            "needs_column_and_multi": (
                "column" in field_names
                and ("column_list" in field_names or "column_set" in field_names)
            ),
            "primary_params": primary_params,
            "advanced_params": advanced_params,
        }

    return catalog


EXPECTATION_CATALOG = _build_catalog()

EXPECTATION_CATEGORIES = [
    category for category in CATEGORY_ORDER
    if any(category in info["categories"] for info in EXPECTATION_CATALOG.values())
]


# ============================================================
# Catalog Access Helpers
# ============================================================

def list_expectations_by_category(category: str) -> list:
    return sorted(
        name for name, info in EXPECTATION_CATALOG.items()
        if category in info["categories"]
    )


def search_expectations(query: str) -> list:
    tokens = query.strip().lower().split()

    if not tokens:
        return []

    matches = []

    for name, info in EXPECTATION_CATALOG.items():
        haystack = f"{name} {info['label']} {info['doc']}".lower()

        if all(token in haystack for token in tokens):
            matches.append(name)

    return sorted(matches)


def get_expectation_schema(expectation_type: str) -> dict:
    return EXPECTATION_CATALOG[expectation_type]


# ============================================================
# Param Parsing Helpers (used by the dynamic form in app.py)
# ============================================================

def _coerce_scalar(token: str):
    try:
        return int(token)
    except ValueError:
        pass

    try:
        return float(token)
    except ValueError:
        pass

    return token


def parse_list_value(text: str) -> list:
    return [
        _coerce_scalar(token.strip())
        for token in text.split(",")
        if token.strip()
    ]


def parse_raw_value(text: str):
    text = text.strip()

    if not text:
        return None

    try:
        return ast.literal_eval(text)
    except (ValueError, SyntaxError):
        return text


def rule_scope_key(kwargs: dict) -> tuple:
    if "column_list" in kwargs:
        return tuple(sorted(kwargs["column_list"]))

    if "column_set" in kwargs:
        return tuple(sorted(kwargs["column_set"]))

    if "column_A" in kwargs and "column_B" in kwargs:
        return tuple(sorted([kwargs["column_A"], kwargs["column_B"]]))

    if "column" in kwargs:
        return (kwargs["column"],)

    return ()


def describe_rule(expectation_type: str, kwargs: dict) -> str:
    info = EXPECTATION_CATALOG.get(expectation_type)

    label = info["label"] if info else expectation_type

    if "column_list" in kwargs:
        scope = ", ".join(str(c) for c in kwargs["column_list"])

    elif "column_set" in kwargs:
        scope = ", ".join(str(c) for c in kwargs["column_set"])

    elif "column_A" in kwargs and "column_B" in kwargs:
        scope = f"{kwargs['column_A']} & {kwargs['column_B']}"

    elif "column" in kwargs:
        scope = str(kwargs["column"])

    else:
        scope = "Table"

    detail_bits = [
        f"{key}={value}"
        for key, value in kwargs.items()
        if key not in _COLUMN_FIELDS and value not in (None, "", [])
    ]

    detail = f" ({', '.join(detail_bits)})" if detail_bits else ""

    return f"{scope}: {label}{detail}"


# ============================================================
# Run Data Quality Checks
# ============================================================

def run_data_quality_checks(df, selected_rules):

    # ============================================================
    # 1. Create Great Expectations Context
    # ============================================================

    context = gx.get_context()


    # ============================================================
    # 2. Create Pandas Data Source
    # ============================================================

    data_source = context.data_sources.add_pandas(
        name="customers_source"
    )


    # ============================================================
    # 3. Create Data Asset
    # ============================================================

    data_asset = data_source.add_dataframe_asset(
        name="customers"
    )


    # ============================================================
    # 4. Create Batch Definition
    # ============================================================

    batch_definition = (
        data_asset.add_batch_definition_whole_dataframe(
            "customers_batch"
        )
    )


    # ============================================================
    # 5. Create Expectation Suite
    # ============================================================

    suite = gx.ExpectationSuite(
        name="dynamic_data_quality_suite"
    )


    # ============================================================
    # 6. Add User-Selected Expectations
    # ============================================================

    for rule in selected_rules:

        expectation_cls = getattr(gxe, rule["expectation_type"])

        suite.add_expectation(
            expectation_cls(**rule["kwargs"])
        )


    # ============================================================
    # 7. Register Expectation Suite
    # ============================================================

    context.suites.add(suite)


    # ============================================================
    # 8. Create Validation Definition
    # ============================================================

    validation_definition = gx.ValidationDefinition(
        data=batch_definition,
        suite=suite,
        name="dynamic_customer_validation"
    )


    # ============================================================
    # 9. Register Validation Definition
    # ============================================================

    validation_definition = (
        context.validation_definitions.add(
            validation_definition
        )
    )


    # ============================================================
    # 10. Run Validation
    # ============================================================

    validation_results = validation_definition.run(
        batch_parameters={
            "dataframe": df
        }
    )


    # ============================================================
    # 11. Transform GX Results
    # ============================================================

    dq_results = []


    for rule, result in zip(selected_rules, validation_results.results):

        validation_result = result.result


        # --------------------------------------------------------
        # Store Clean Result
        # --------------------------------------------------------

        dq_results.append({

            "rule": describe_rule(
                rule["expectation_type"],
                rule["kwargs"]
            ),

            "status": (
                "PASS"
                if result.success
                else "FAIL"
            ),

            "checked": validation_result.get(
                "element_count",
                0
            ),

            "failed": validation_result.get(
                "unexpected_count",
                0
            ),

            "failure_percent": validation_result.get(
                "unexpected_percent",
                0
            )
        })


    # ============================================================
    # 12. Get Overall GX Statistics
    # ============================================================

    statistics = validation_results.statistics


    summary = {

        "total_rules": statistics[
            "evaluated_expectations"
        ],

        "passed": statistics[
            "successful_expectations"
        ],

        "failed": statistics[
            "unsuccessful_expectations"
        ],

        "dq_score": statistics[
            "success_percent"
        ]
    }


    # ============================================================
    # 13. Return Clean Result
    # ============================================================

    return {

        "summary": summary,

        "rules": dq_results

    }
