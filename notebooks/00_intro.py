import marimo

__generated_with = "0.18.3"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo

    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 1. Reactivity
    """)
    return


@app.cell
def _():
    a = 1
    return (a,)


@app.cell
def _():
    b = 2
    return (b,)


@app.cell
def _(a, b):
    c = a + b
    c
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 2. Cell Types
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Python**
    """)
    return


@app.cell
def _():
    import polars as pl

    df = pl.read_parquet(
        "https://github.com/uwdata/mosaic/raw/main/data/athletes.parquet"
    )
    df
    return (df,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **SQL**
    """)
    return


@app.cell
def _(df, mo):
    result = mo.sql(
        f"""
        SELECT sport, COUNT(*) as count
        FROM df
        GROUP BY sport
        ORDER BY count DESC
        LIMIT 10
        """
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Markdown**
    """)
    return


@app.cell
def _(mo):
    mo.md(r"""
    You can write **bold**, _italic_, and `code`.

    - Lists
    - Are
    - Easy
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 3. UI Elements

    Interacting with a UI element automatically triggers execution of cells that reference it.
    """)
    return


@app.cell
def _(mo):
    icon = mo.ui.dropdown(["🍃", "🌊", "✨"], value="🍃")
    icon
    return (icon,)


@app.cell
def _(mo):
    repetitions = mo.ui.slider(0, 10, 1)
    repetitions
    return (repetitions,)


@app.cell
def _(icon, mo, repetitions):
    mo.md("# " + icon.value * repetitions.value)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 4. Notebook or App?

    Click the app window icon (bottom-right) to see this notebook in "app view."

    Serve any notebook as an app with `marimo run notebook.py`.
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## 5. Other Editor Features

    - [Variables panel](https://docs.marimo.io/guides/editor_features/overview.html)
    - [Dataflow](https://docs.marimo.io/guides/editor_features/dataflow/) — dependency explorer, minimap
    - [Package management](https://docs.marimo.io/guides/editor_features/package_management.html)
    - [Chat and agents](https://docs.marimo.io/guides/ai_completion.html)
    - `mo.inspect()` — inspect any "live" object
    """)
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
