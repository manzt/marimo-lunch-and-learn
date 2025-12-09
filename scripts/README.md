Scripts to produce `notebooks/tsne.parquet`

1. Download all Open NGA image thumbnails:

   ```bash
   cargo run --release
   ```

1. Generate embeddings from images using DINOv2:

   ```bash
   uv run embed.py -i <images_dir> -o embeddings.npz
   ```

2. Run t-SNE on the embeddings:

   ```bash
   uv run tsne.py
   ```
