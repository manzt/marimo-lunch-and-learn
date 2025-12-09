import marimo

__generated_with = "0.23.1"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## The Dataset

    The [National Gallery of Art Open Data](https://www.nga.gov/open-access-images/open-data.html)
    provides metadata for **130,000+ artworks** under CC0 license — titles, dates, artists,
    and classifications are all free to use. The collection spans paintings, prints, drawings,
    photographs, and sculptures by artists like van Gogh, Picasso, and Georgia O'Keeffe.

    However, the *images* have separate licensing. Only about half are public domain (CC0),
    meaning they can be freely downloaded and shared. This info isn't in the dataset itself,
    so we've pre-fetched the public domain IDs separately.

    We'll load and join several tables to create a unified view of the collection.
    """)
    return


@app.cell
def _(load_data):
    df = load_data()
    return (df,)


@app.cell(hide_code=True)
def _():
    import polars as pl
    import marimo as mo
    import pathlib


    @mo.persistent_cache
    def load_data(
        base="https://raw.githubusercontent.com/NationalGalleryOfArt/opendata/main/data",
    ) -> pl.DataFrame:
        objects = pl.read_csv(f"{base}/objects.csv", infer_schema_length=10000)
        constituents = pl.read_csv(
            f"{base}/constituents.csv", infer_schema_length=10000
        )
        obj_constituents = pl.read_csv(
            f"{base}/objects_constituents.csv",
            infer_schema_length=10000,
            schema_overrides={"zipcode": pl.Utf8},
        )
        images = pl.read_csv(
            f"{base}/published_images.csv", infer_schema_length=10000
        )
        artists = (
            obj_constituents.filter(pl.col("roletype") == "artist")
            .sort("displayorder")
            .group_by("objectid")
            .first()
            .join(
                constituents.select(
                    "constituentid",
                    pl.col("preferreddisplayname").alias("artist"),
                    pl.col("nationality").alias("artist_nationality"),
                ),
                on="constituentid",
            )
            .select("objectid", "artist", "artist_nationality")
        )

        thumbnails = (
            images.filter(
                (pl.col("viewtype") == "primary") & (pl.col("sequence") == 0)
            )
            .group_by("depictstmsobjectid")
            .first()
            .select(
                pl.col("depictstmsobjectid").alias("objectid"),
                pl.col("iiifthumburl").alias("thumbnail"),
                pl.col("iiifurl").alias("iiif_url"),
                "width",
                "height",
                pl.col("openaccess").alias("public_domain"),
            )
        )
        tsne = pl.read_parquet(pathlib.Path(__file__).parent / "tsne.parquet")

        return (
            objects.select(
                "objectid",
                "title",
                pl.col("displaydate").alias("date"),
                "beginyear",
                "medium",
                "classification",
            )
            .join(artists, on="objectid", how="left")
            .join(thumbnails, on="objectid", how="left")
            .join(tsne, on="objectid", how="left")
            .filter(
                pl.col("thumbnail").is_not_null(),
                pl.col("x").is_not_null(),
                pl.col("y").is_not_null(),
            )
            .with_columns(pl.col("public_domain").cast(pl.Boolean))
            .select(
                "thumbnail",
                "iiif_url",
                "title",
                "artist",
                "artist_nationality",
                "date",
                "beginyear",
                "medium",
                pl.col("classification").alias("type"),
                "width",
                "height",
                pl.col("public_domain").alias("public"),
                "x",
                "y",
            )
        )

    return load_data, mo, pl


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Plot distributions
    """)
    return


@app.cell
def _(df):
    import altair as alt

    alt.data_transformers.enable("vegafusion")

    alt.Chart(df).mark_bar().encode(
        x=alt.X("type", sort="-y", title="Type"),
        y=alt.Y("count()", title="Count"),
        color=alt.Color("public", title="Public domain"),
    )
    return (alt,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ### Define a subset
    """)
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    programatically...
    """)
    return


@app.cell
def _(df):
    # full dataset
    subset = df
    # just the paintings
    # _subset = df.filter(pl.col("type") == "painting")
    return (subset,)


@app.cell
def _(alt, subset):
    alt.Chart(
        subset.group_by("artist", "public")
        .len()
        .sort("len", descending=True)
        .head(15)
    ).mark_bar().encode(
        x=alt.X("len", title="Count"),
        y=alt.Y("artist", title="Artist", sort="-x"),
        color=alt.Color("public", title="Public domain"),
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    interactively (with [quak](https://github.com/manzt/quak))...
    """)
    return


@app.cell(hide_code=True)
def _(df, mo):
    import quak

    table = mo.ui.anywidget(quak.Widget(df))
    table
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## GalleryWidget

    Custom anywidget to browse artwork thumbnails. Click to open on NGA website.
    """)
    return


@app.cell
def _(GalleryWidget, pl, subset):
    GalleryWidget(
        data=subset.filter(pl.col("public")).sample(500, seed=42), page_size=15
    )
    return


@app.cell(hide_code=True)
def _(pl):
    import anywidget
    import traitlets


    class GalleryWidget(anywidget.AnyWidget):
        """Paginated mosaic gallery with multi-select and right-click detail."""

        _data = traitlets.Any(b"").tag(sync=True)
        selected = traitlets.List([]).tag(sync=True)
        page_size = traitlets.Int(60).tag(sync=True)

        def __init__(self, data: pl.DataFrame, **kwargs):
            buf = data.write_ipc(None)
            assert buf is not None
            kwargs["_data"] = buf.getvalue()
            super().__init__(**kwargs)

        _esm = """
    import { tableFromIPC } from "https://esm.sh/@uwdata/flechette@2";
    function render({ model, el }) {
      const controller = new AbortController();
      const { signal } = controller;
      let currentPage = 0;
      let table = null;
      function parseTable() {
        const buf = model.get("_data");
        if (buf && buf.byteLength) {
          table = tableFromIPC(new Uint8Array(buf.buffer));
        }
      }
      const style = document.createElement("style");
      style.textContent = `
        .gallery-root { font-family: system-ui, sans-serif; }
        .gallery-grid {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
          gap: 6px;
          padding: 4px;
          grid-auto-rows: 8px;
        }
        @supports (display: grid-lanes) {
          .gallery-grid {
            display: grid-lanes;
            grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
            gap: 6px;
            padding: 4px;
          }
        }
        .gallery-card {
          position: relative; cursor: pointer; border-radius: 6px;
          overflow: hidden; background: #f0f0f0;
          border: 3px solid transparent; transition: border-color 0.15s;
        }
        .gallery-card.selected { border-color: #3b82f6; }
        .gallery-card img { width: 100%; display: block; }
        .gallery-overlay {
          position: absolute; bottom: 0; left: 0; right: 0;
          background: linear-gradient(transparent, rgba(0,0,0,.75));
          color: white; padding: 20px 6px 6px; font-size: 11px;
          opacity: 0; transition: opacity 0.15s; pointer-events: none;
        }
        .gallery-card:hover .gallery-overlay { opacity: 1; }
        .gallery-nav {
          display: flex; align-items: center; justify-content: center;
          gap: 8px; padding: 8px 0; user-select: none;
        }
        .gallery-nav button {
          padding: 4px 14px; border: 1px solid #ccc; border-radius: 6px;
          background: white; color: #333; cursor: pointer; font-size: 13px;
        }
        .gallery-nav button:disabled { opacity: 0.4; cursor: default; }
        .gallery-nav span { font-size: 13px; color: #555; min-width: 120px; text-align: center; }
        dialog.gallery-popup {
          border: 1px solid #ccc; border-radius: 12px; padding: 0;
          max-width: 480px; width: 90vw; box-shadow: 0 8px 32px rgba(0,0,0,.25);
          overflow: hidden;
        }
        dialog.gallery-popup::backdrop { background: rgba(0,0,0,.4); }
      `;
      el.appendChild(style);
      const root = document.createElement("div");
      root.className = "gallery-root";
      const nav = document.createElement("div");
      nav.className = "gallery-nav";
      const prevBtn = document.createElement("button");
      prevBtn.textContent = "\u2190 Prev";
      const pageInfo = document.createElement("span");
      const nextBtn = document.createElement("button");
      nextBtn.textContent = "Next \u2192";
      nav.append(prevBtn, pageInfo, nextBtn);
      const grid = document.createElement("div");
      grid.className = "gallery-grid";
      const popup = document.createElement("dialog");
      popup.className = "gallery-popup";
      popup.addEventListener("click", (e) => { if (e.target === popup) popup.close(); }, { signal });
      root.append(nav, grid, popup);
      el.appendChild(root);
      function val(name, i) { return table.getChild(name).at(i); }
      function totalPages() {
        if (!table) return 1;
        return Math.max(1, Math.ceil(table.numRows / model.get("page_size")));
      }
      function buildGrid() {
        grid.innerHTML = "";
        if (!table) { pageInfo.textContent = "No data"; return; }
        const ps = model.get("page_size");
        const selected = new Set(model.get("selected"));
        const start = currentPage * ps;
        const end = Math.min(start + ps, table.numRows);
        prevBtn.disabled = currentPage === 0;
        nextBtn.disabled = currentPage >= totalPages() - 1;
        pageInfo.textContent = `Page ${currentPage + 1} of ${totalPages()} (${table.numRows.toLocaleString()} total)`;
        const ROW_H = 8;
        const GAP = 6;
        for (let globalIdx = start; globalIdx < end; globalIdx++) {
          const w = val("width", globalIdx) || 1;
          const h = val("height", globalIdx) || 1;
          const ratio = h / w;
          const card = document.createElement("div");
          card.className = "gallery-card" + (selected.has(globalIdx) ? " selected" : "");
          const estHeight = 120 * ratio;
          const span = Math.max(2, Math.ceil((estHeight + GAP) / (ROW_H + GAP)));
          card.style.gridRowEnd = `span ${span}`;
          const img = document.createElement("img");
          img.src = val("thumbnail", globalIdx);
          img.alt = val("title", globalIdx) ?? "";
          img.loading = "lazy";
          card.appendChild(img);
          const overlay = document.createElement("div");
          overlay.className = "gallery-overlay";
          overlay.textContent = val("title", globalIdx) ?? "";
          card.appendChild(overlay);
          card.addEventListener("click", (e) => {
            if (e.metaKey || e.ctrlKey) {
              const iiif = val("iiif_url", globalIdx);
              window.open(iiif + "/full/full/0/default.jpg", "_blank");
              return;
            }
            const sel = new Set(model.get("selected"));
            if (e.shiftKey) {
              sel.has(globalIdx) ? sel.delete(globalIdx) : sel.add(globalIdx);
            } else {
              if (sel.size === 1 && sel.has(globalIdx)) sel.clear();
              else { sel.clear(); sel.add(globalIdx); }
            }
            model.set("selected", [...sel].sort((a, b) => a - b));
            model.save_changes();
          }, { signal });
          card.addEventListener("contextmenu", (e) => {
            e.preventDefault();
            const iiif = val("iiif_url", globalIdx);
            popup.innerHTML = `
              <img src="${iiif}/full/!800,800/0/default.jpg"
                   style="width:100%;display:block;background:#000;" />
              <div style="padding:16px;">
                <h3 style="margin:0 0 4px;">${val("title", globalIdx) ?? ""}</h3>
                <p style="margin:0 0 2px;color:#555;">${val("artist", globalIdx) ?? "Unknown artist"}</p>
                <p style="margin:0 0 2px;color:#777;font-size:13px;">${val("date", globalIdx) ?? ""}</p>
                <p style="margin:0 0 2px;color:#777;font-size:13px;">${val("medium", globalIdx) ?? ""}</p>
                <p style="margin:0;color:#777;font-size:13px;">${val("type", globalIdx) ?? ""}</p>
              </div>
            `;
            popup.showModal();
          }, { signal });
          grid.appendChild(card);
        }
      }
      prevBtn.addEventListener("click", () => {
        if (currentPage > 0) { currentPage--; buildGrid(); grid.scrollTop = 0; }
      }, { signal });
      nextBtn.addEventListener("click", () => {
        if (currentPage < totalPages() - 1) { currentPage++; buildGrid(); grid.scrollTop = 0; }
      }, { signal });
      model.on("change:_data", () => { parseTable(); currentPage = 0; buildGrid(); });
      model.on("change:selected", buildGrid);
      parseTable();
      buildGrid();
      return () => controller.abort();
    }
    export default { render };
    """

    return (GalleryWidget,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Explore
    """)
    return


@app.cell
def _(df, mo):
    import jscatter

    # jupyter-scatter requires pandas
    pdf = df.to_pandas()

    scatter = jscatter.Scatter(x="x", y="y", data=pdf)
    scatter.height(500)
    scatter.color(by="type")
    scatter.legend(True)
    scatter.tooltip(True, preview="thumbnail", preview_type="image")

    get_selection, set_selection = mo.state(scatter.widget.selection)
    scatter.widget.observe(
        lambda _: set_selection(scatter.widget.selection), names=["selection"]
    )
    scatter.widget
    return get_selection, pdf


@app.cell
def _(GalleryWidget, get_selection, pdf, pl):
    GalleryWidget(
        data=pl.from_pandas(pdf.iloc[get_selection()]),
        page_size=20,
    )
    return


@app.cell
def _():
    return


if __name__ == "__main__":
    app.run()
