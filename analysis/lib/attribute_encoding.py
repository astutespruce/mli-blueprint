import pandas as pd

from analysis.constants import BLUEPRINT, INDICATORS


def encode_values(df, total, scale=100):
    """Convert a dataframe from acres to integer scalar values:
    scale * value / total

    This can be used to express percent where scale = 100

    Values are packed into a pipe-delimited string with 0 values omitted, e.g.,
    '10|20|70||'

    Parameters
    ----------
    df : DataFrame
        Note: only includes columns to be divided by total.
    total : ndarray
        Must be in same order as df and be greater than 0.

    Returns
    -------
    Series
        Contains string for each record with pipe-delimited values.  If
        max encoded value across all bins is 0, an empty string is returned instead.
    """
    return (
        (scale * df.divide(total, axis=0))
        .round()
        .astype("uint")
        .apply(lambda r: "|".join(str(v or "") for v in r) if r.max() else "", axis=1)
    )


def delta_encode_values(df, total, scale=100):
    """Convert a dataframe from acres to delta-encoded integer scalar values,
    where original values are first scaled.

    This can be used to express percent where scale = 100.

    Values are packed into a caret-delimited string with 0 values omitted, e.g.,
    '<baseline_value>^<delta_value1>^<delta_value2>...'

    If there is no change from the baseline value, that value plus an indication
    of number of values is returned instead:
    '<baseline_value>x<num_values>'


    Parameters
    ----------
    df : DataFrame
        Note: only includes columns to be divided by total.
    total : ndarray
        Representative acres of record in df; must be in same order as df and
        be greater than 0.

    Returns
    -------
    Series
        Contains string for each record with caret-delimited values.  If
        max encoded value across all bins is 0, an empty string is returned instead.
    """

    # NOTE: this breaks for uint if series is not always incremental, so we use
    # int here
    scaled = (scale * df.divide(total, axis=0)).round().astype("int")

    # calculate delta values
    delta = scaled[scaled.columns[1:]].subtract(scaled[scaled.columns[:-1]].values, axis=0)

    # caret must be escaped
    # nochange = "\^" * len(delta.columns)

    return (
        scaled[[scaled.columns[0]]]
        .join(delta)
        .apply(lambda r: "^".join(str(v or "") for v in r) if r.max() else "", axis=1)
    )


def encode_blueprint(df):
    """Encode Blueprint and indicators

    Parameters
    ----------
    df : DataFrame
        must include "rasterized_acres"

    Returns
    -------
    DataFrame
    """
    blueprint_cols = [f"blueprint_{v['value']}" for v in BLUEPRINT]
    blueprint = encode_values(
        df[blueprint_cols],
        df.rasterized_acres,
        1000,
    ).rename("blueprint")

    # only check areas of indicators actually present in summaries for unit type
    check_indicators = {e["id"]: e for e in INDICATORS if f"{e['id']}_outside" in df.columns}

    # NOTE: serialized indicator ID is its position in full indicators list
    # join to empty data frame to have full index
    indicators = df[[]]
    for i, id in enumerate([i["id"] for i in INDICATORS]):
        if id not in check_indicators:
            continue

        indicator = check_indicators[id]
        values = indicator["values"]
        cols = [f"{id}_value_{v['value']}" for v in values]
        indicator_acres = df[cols]
        total_acres = indicator_acres.sum(axis=1)

        # drop any entries where they are not present or are only 0 values for
        # indicators with 0 values
        indicator_acres = indicator_acres.loc[
            (total_acres > 0) & ~((values[0]["value"] == 0) & (indicator_acres[cols[1:]].max(axis=1) == 0))
        ]

        if len(indicator_acres) == 0:
            continue

        indicator_acres = indicator_acres.join(df.rasterized_acres)
        encoded = encode_values(indicator_acres[cols], indicator_acres.rasterized_acres, 1000).rename(i)

        indicators = indicators.join(encoded, how="left")

    indicators = (
        indicators.fillna("")
        .apply(lambda row: ",".join((f"{k}:{v}" for k, v in row.items() if v)), axis=1)
        .rename("indicators")
    )

    return pd.DataFrame(blueprint).join(indicators)
