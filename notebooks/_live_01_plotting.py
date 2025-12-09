import marimo

__generated_with = "0.18.4"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Load Data
    """)
    return


@app.cell
def _():
    import marimo as mo
    from altair.datasets import data

    cars = data.cars()
    cars
    return cars, mo


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Static Plots
    """)
    return


@app.cell
def _(cars):
    import seaborn as sns

    sns.scatterplot(
        data=cars, x="Horsepower", y="Miles_per_Gallon", hue="Origin", alpha=0.7
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Compose with UI elements:
    """)
    return


@app.cell
def _():
    color_by = ["Origin", "Cylinders", "Year"]
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    What if we want to inspect a specific point? We have to **manually filter**:
    """)
    return


@app.cell
def _():
    # interesting subset?
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. Interactive Plots (Altair)
    """)
    return


@app.cell
def _(cars):
    import altair as alt

    brush = alt.selection_interval()

    points = (
        alt.Chart(cars)
        .mark_point()
        .encode(
            x="Horsepower",
            y="Miles_per_Gallon",
            color=alt.condition(brush, "Origin", alt.value("lightgray")),
            tooltip=["Name"],
        )
        .add_params(brush)
    )

    bars = (
        points.mark_bar()
        .encode(x="count()", y="Origin", color="Origin")
        .transform_filter(brush)
    )

    points & bars
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    Selection is "trapped" in JS — can't access it in Python.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. `mo.ui.altair_chart()`
    """)
    return


@app.cell
def _():
    # mo.ui.altair_chart
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. anywidget

    Extend marimo yourself with [anywidget](https://anywidget.dev)!
    """)
    return


@app.cell
def _():
    # https://anywidget.dev
    return


if __name__ == "__main__":
    app.run()
