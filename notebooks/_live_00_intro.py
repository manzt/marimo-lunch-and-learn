import marimo

__generated_with = "0.18.4"
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
    # https://github.com/uwdata/mosaic/raw/main/data/athletes.parquet
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **SQL**
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    **Markdown**
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
def _():
    icons = ["🍃", "🌊", "✨"]
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
