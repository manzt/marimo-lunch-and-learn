# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "numpy",
#     "polars",
#     "scikit-learn",
# ]
#
# [tool.uv]
# exclude-newer = "2025-12-09T06:40:36.036728-08:00"
# ///
import argparse
import pathlib

import numpy as np
import polars as pl
from sklearn.manifold import TSNE

SELF_DIR = pathlib.Path(__file__).parent


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run t-SNE dimensionality reduction on image embeddings."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=pathlib.Path,
        default=SELF_DIR / "embeddings.npz",
        help="Input embeddings file",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=pathlib.Path,
        default=SELF_DIR / "../notebooks/tsne.parquet",
        help="Output parquet file",
    )
    args = parser.parse_args()

    raw = np.load(args.input)
    object_ids, X = raw["object_ids"], raw["embeddings"]

    config = {"perplexity": 50, "learning_rate": "auto"}
    print(f"Running t-SNE with {config}")

    tsne = TSNE(n_components=2, random_state=42, **config)
    X_transformed = tsne.fit_transform(X)

    (
        pl.DataFrame(
            {
                "objectid": object_ids,
                "x": X_transformed[:, 0],
                "y": X_transformed[:, 1],
            }
        )
        .with_columns(
            pl.col("objectid").cast(pl.Int32),
            pl.col("x").cast(pl.Float32),
            pl.col("y").cast(pl.Float32),
        )
        .write_parquet(args.output)
    )

    print(f"Saved to {args.output}")


if __name__ == "__main__":
    main()
