# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "pillow",
#     "torch",
#     "torchvision",
#     "tqdm",
#     "transformers",
# ]
#
# [tool.uv]
# exclude-newer = "2025-12-09T06:40:36.036728-08:00"
# ///
"""
Batch image embedding script using DINOv2.
"""

import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm
from transformers import AutoImageProcessor, AutoModel


class ImageFolderDataset(Dataset):
    """Dataset that loads images from a folder."""

    def __init__(self, image_dir: Path, processor):
        self.processor = processor
        self.image_paths = sorted(image_dir.glob("*.jpg"))
        self.object_ids = [int(f.stem) for f in self.image_paths]

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        path = self.image_paths[idx]
        obj_id = self.object_ids[idx]

        try:
            image = Image.open(path).convert("RGB")
            inputs = self.processor(images=image, return_tensors="pt")
            pixel_values = inputs["pixel_values"].squeeze(0)
            return {"pixel_values": pixel_values, "object_id": obj_id, "valid": True}
        except Exception as e:
            # Return a dummy tensor for failed images
            print(f"Failed to load {path}: {e}")
            return {
                "pixel_values": torch.zeros(3, 224, 224),
                "object_id": obj_id,
                "valid": False,
            }


def collate_fn(batch):
    """Custom collate that handles failed images."""
    valid_mask = [item["valid"] for item in batch]
    pixel_values = torch.stack([item["pixel_values"] for item in batch])
    object_ids = [item["object_id"] for item in batch]
    return {
        "pixel_values": pixel_values,
        "object_ids": object_ids,
        "valid_mask": valid_mask,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Generate image embeddings with DINOv2"
    )
    parser.add_argument(
        "-i", "--input", type=Path, default=Path("images"), help="Input image directory"
    )
    parser.add_argument(
        "-o", "--output", type=Path, default=Path("embeddings.npz"), help="Output file"
    )
    parser.add_argument("-b", "--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument(
        "-w", "--workers", type=int, default=4, help="DataLoader workers"
    )
    parser.add_argument(
        "--model", type=str, default="facebook/dinov2-base", help="Model name"
    )
    args = parser.parse_args()

    # Device setup
    if torch.cuda.is_available():
        device = torch.device("cuda")
        print(f"Using CUDA: {torch.cuda.get_device_name()}")
    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        print("Using Apple MPS")
    else:
        device = torch.device("cpu")
        print("Using CPU")

    # Load model
    print(f"Loading model: {args.model}")
    processor = AutoImageProcessor.from_pretrained(args.model, use_fast=True)
    model = AutoModel.from_pretrained(args.model)
    model = model.to(device)
    model.eval()

    # Create dataset
    dataset = ImageFolderDataset(args.input, processor)
    print(f"Found {len(dataset)} images to process")

    dataloader = DataLoader(
        dataset,
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        collate_fn=collate_fn,
        pin_memory=True if device.type == "cuda" else False,
    )

    # Process batches
    all_embeddings = []
    all_object_ids = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc="Embedding"):
            pixel_values = batch["pixel_values"].to(device)
            object_ids = batch["object_ids"]
            valid_mask = batch["valid_mask"]

            # Forward pass
            outputs = model(pixel_values)

            # Mean pool over patch tokens -> [batch, hidden_dim]
            embeddings = outputs.last_hidden_state.mean(dim=1)
            embeddings = embeddings.cpu().numpy()

            # Only keep valid embeddings
            for emb, obj_id, valid in zip(embeddings, object_ids, valid_mask):
                if valid:
                    all_embeddings.append(emb)
                    all_object_ids.append(obj_id)

    # Save results
    print(f"Saving {len(all_object_ids)} embeddings to {args.output}")
    np.savez_compressed(
        args.output,
        embeddings=np.array(all_embeddings, dtype=np.float32),
        object_ids=np.array(all_object_ids, dtype=np.int32),
    )

    # Print stats
    embeddings_array = np.array(all_embeddings)
    print(f"Embedding shape: {embeddings_array.shape}")
    print(f"File size: {args.output.stat().st_size / 1024 / 1024:.1f} MB")


if __name__ == "__main__":
    main()
