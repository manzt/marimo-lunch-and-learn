import marimo

__generated_with = "0.18.3"
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
    return (sns,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Compose with UI elements:
    """)
    return


@app.cell
def _(mo):
    color_by = mo.ui.dropdown(
        ["Origin", "Cylinders", "Year"],
        value="Origin",
        label="Color by",
    )
    color_by
    return (color_by,)


@app.cell
def _(cars, color_by, sns):
    sns.scatterplot(data=cars, x="Horsepower", y="Miles_per_Gallon", hue=color_by.value, alpha=0.7)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    What if we want to inspect a specific point? We have to **manually filter**:
    """)
    return


@app.cell
def _(cars):
    interesting_point = cars[
        (cars["Miles_per_Gallon"] > 30)
        & (cars["Miles_per_Gallon"] < 35)
        & (cars["Horsepower"] > 125)
        & (cars["Horsepower"] < 150)
    ]
    interesting_point
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
    return bars, points


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
def _(bars, mo, points):
    chart = mo.ui.altair_chart(points & bars)
    chart
    return (chart,)


@app.cell
def _(chart):
    chart.value
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
    import anywidget
    import traitlets

    class Counter(anywidget.AnyWidget):
        _esm = """
        function render({ model, el }) {
          let button = document.createElement("button");
          button.innerHTML = `count is ${model.get("count")}`;
          button.addEventListener("click", () => {
            model.set("count", model.get("count") + 1);
            model.save_changes();
          });
          model.on("change:count", () => {
            button.innerHTML = `count is ${model.get("count")}`;
          });
          el.classList.add("counter-widget");
          el.appendChild(button);
        }
        export default { render };
        """
        _css = """
        button {
            color: white;
            font-size: 1.75rem;
            background-color: #ea580c;
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 0.25rem;
        }
        button:hover {
            background-color: #9a3412;
        }
        """
        count = traitlets.Int(0).tag(sync=True)

    counter = Counter(count=42)
    counter
    return (counter,)


@app.cell
def _(mo):
    slider = mo.ui.slider(0, 360, 1)
    slider
    return (slider,)


@app.cell
def _(counter, slider):
    # Assignment triggers widget update
    counter.count = slider.value
    return


if __name__ == "__main__":
    app.run()
