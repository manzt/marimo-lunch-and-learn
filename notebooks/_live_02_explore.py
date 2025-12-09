import marimo

__generated_with = "0.18.4"
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
    df
    return (df,)


@app.cell
def _():
    import polars as pl
    import marimo as mo
    import pathlib


    def load_data() -> pl.DataFrame:
        # curated set of images in public domain
        public_domain_ids = [
            int(id)
            for id in (pathlib.Path(__file__).parent / "public_domain_ids.txt")
            .read_text(encoding="utf8")
            .split("\n")
        ]

        # rest of the public database dump
        url = "https://github.com/NationalGalleryOfArt/opendata/raw/refs/heads/main/data/"

        # projections generated from scripts/
        tsne = pl.read_parquet(pathlib.Path(__file__).parent / "tsne.parquet")

        objects = pl.read_csv(url + "objects.csv", ignore_errors=True).select(
            pl.col("objectid"),
            pl.col("title"),
            pl.col("beginyear").alias("year"),
            pl.col("medium"),
            pl.col("visualbrowserclassification").alias("type"),
        )

        constituents = pl.read_csv(
            url + "constituents.csv", ignore_errors=True
        ).select(
            pl.col("constituentid"),
            pl.col("forwarddisplayname").alias("name"),
            pl.col("visualbrowsernationality").alias("nationality"),
        )

        published_images = pl.read_csv(url + "published_images.csv").select(
            pl.col("depictstmsobjectid").alias("objectid"),
            pl.col("uuid"),
            pl.col("iiifthumburl").alias("thumburl"),
        )

        objects_constituents = (
            pl.read_csv(url + "objects_constituents.csv", ignore_errors=True)
            .filter(pl.col("role").eq(pl.lit("artist")))
            .sort(by="displayorder")
            .group_by("objectid")
            .first()
            .select("objectid", "constituentid")
        )

        return (
            objects.join(objects_constituents, on="objectid")
            .join(constituents, on="constituentid")
            .join(published_images, on="objectid")
            .join(tsne, on="objectid")
            .select(pl.col("thumburl"), pl.exclude("constituentid", "thumburl"))
            .with_columns(
                pl.col("objectid").is_in(public_domain_ids).alias("public")
            )
            .sort(by="year", descending=True, nulls_last=True)
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
        subset.group_by("name", "public")
        .len()
        .sort("len", descending=True)
        .head(15)
    ).mark_bar().encode(
        x=alt.X("len", title="Count"),
        y=alt.Y("name", title="Artist", sort="-x"),
        color=alt.Color("public", title="Public domain"),
    )
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    interactively (with [quak](https://github.com/manzt/quak))...
    """)
    return


@app.cell
def _():
    import quak
    return


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## GalleryWidget

    Custom anywidget to browse artwork thumbnails. Click to open on NGA website.
    """)
    return


@app.cell
def _(GalleryWidget, subset):
    GalleryWidget(subset.sample(500, seed=42))
    return


@app.cell
def _(GALLERY_WIDGET_ESM, GALLERY_WIDGET_STYLES, pl):
    import anywidget
    import traitlets

    class GalleryWidget(anywidget.AnyWidget):
        _esm = GALLERY_WIDGET_ESM
        _css = GALLERY_WIDGET_STYLES

        _ipc = traitlets.Any().tag(sync=True)
        size = traitlets.Int(100).tag(sync=True)
        page = traitlets.Int(0).tag(sync=True)
        page_size = traitlets.Int(12).tag(sync=True)

        def __init__(
            self, objects: pl.DataFrame, *, size: int = 90, page_size: int = 20
        ) -> None:
            super().__init__(
                _ipc=objects.write_ipc(None).getvalue(),
                size=size,
                page=0,
                page_size=page_size,
            )
    return (GalleryWidget,)


@app.cell(hide_code=True)
def _():
    GALLERY_WIDGET_ESM = """
    import * as flech from "https://esm.sh/@uwdata/flechette@2.0.0";

    function render({ model, el }) {
      let objects = flech.tableFromIPC(new Uint8Array(model.get("_ipc").buffer));

      let container = document.createElement("div");
      container.className = "gallery";

      let paginationControls = document.createElement("div");
      paginationControls.className = "pagination-controls";

      let prevButton = document.createElement("button");
      prevButton.innerText = "← Previous";

      let pageIndicator = document.createElement("span");
      pageIndicator.className = "page-indicator";
      let nextButton = document.createElement("button");
      nextButton.innerText = "Next →";

      paginationControls.appendChild(prevButton);
      paginationControls.appendChild(pageIndicator);
      paginationControls.appendChild(nextButton);

      el.appendChild(container);
      el.appendChild(paginationControls);

      function update() {
        container.replaceChildren();

        let size = model.get("size");
        let page = model.get("page");
        let pageSize = model.get("page_size");
        let totalPages = Math.ceil(objects.numRows / pageSize);

        container.style.gridTemplateColumns = `repeat(auto-fill, minmax(${size}px, 1fr))`;

        let startIdx = page * pageSize;
        let endIdx = Math.min(startIdx + pageSize, objects.numRows);

        for (let i = startIdx; i < endIdx; i++) {
          let row = objects.get(i);
          let item = document.createElement("div");
          item.className = "gallery-item";

          let link = Object.assign(document.createElement("a"), {
            className: "thumb-link",
            href: `https://www.nga.gov/collection/art-object-page.${row.objectid}.html`,
            target: "_blank",
            rel: "noopener noreferrer",
          });
          link.style.width = `${size}px`;
          link.style.height = `${size}px`;

          let img = Object.assign(document.createElement("img"), {
            src: row.thumburl,
            alt: row.title,
          });
          link.appendChild(img);

          if (row.public) {
            let badge = Object.assign(document.createElement("img"), {
              src: "https://mirrors.creativecommons.org/presskit/icons/zero.svg",
              alt: "Public Domain",
              className: "public-domain-badge",
            });
            link.appendChild(badge);
          }

          item.appendChild(link);
          container.appendChild(item);
        }

        pageIndicator.innerText = `Page ${page + 1} of ${totalPages}`;
        prevButton.disabled = page <= 0;
        nextButton.disabled = page >= totalPages - 1;
      }

      update();

      prevButton.addEventListener("click", () => {
        let page = model.get("page");
        if (page > 0) {
          model.set("page", page - 1);
          model.save_changes();
        }
      });

      nextButton.addEventListener("click", () => {
        let page = model.get("page");
        let pageSize = model.get("page_size");
        let totalPages = Math.ceil(objects.numRows / pageSize);

        if (page < totalPages - 1) {
          model.set("page", page + 1);
          model.save_changes();
        }
      });

      model.on("change:page", update);
      model.on("change:size", update);
      model.on("change:page_size", update);
    }

    export default { render };
    """

    GALLERY_WIDGET_STYLES = """
    .gallery {
      display: grid;
      gap: 8px;
      margin-bottom: 15px;
    }
    .gallery-item {
      position: relative;
      text-align: center;
    }
    .thumb-link {
      display: block;
      position: relative;
    }
    .thumb-link img:first-child {
      width: 100%;
      height: 100%;
      object-fit: cover;
      border-radius: 5px;
    }
    .public-domain-badge {
      position: absolute;
      bottom: 3px;
      right: 3px;
      width: 20px;
      height: 20px;
      opacity: 0.6;
    }
    .pagination-controls {
      display: flex;
      justify-content: center;
      align-items: center;
      margin-top: 10px;
      gap: 15px;
    }
    .pagination-controls button {
      padding: 5px 10px;
      background-color: var(--background);
      border: 1px solid #ccc;
      border-radius: 4px;
      cursor: pointer;
    }
    .pagination-controls button:disabled {
      background-color: var(--background);
      color: #999;
      cursor: not-allowed;
    }
    .page-indicator {
      font-size: 14px;
    }
    """
    return GALLERY_WIDGET_ESM, GALLERY_WIDGET_STYLES


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    ## Explore
    """)
    return


@app.cell
def _(df):
    import jscatter

    # jupyter-scatter requires pandas
    pdf = df.to_pandas()

    scatter = jscatter.Scatter(x="x", y="y", data=pdf)
    scatter.height(500)
    scatter.color(by="type")
    scatter.legend(True)
    scatter.tooltip(True, preview="thumburl", preview_type="image")

    # w = mo.ui.anywidget(scatter.widget)
    # w
    return


@app.cell
def _():
    # GalleryWidget(pl.from_pandas(pdf.iloc[w.selection]))
    return


if __name__ == "__main__":
    app.run()
