from pathlib import Path

from datasets import load_dataset

OUT_PATH = Path("data/raw/criteo-uplift.csv")


def main() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    dataset = load_dataset("criteo/criteo-uplift", split="train")
    df = dataset.to_pandas()
    df.to_csv(OUT_PATH, index=False)

    print(f"Saved dataset to {OUT_PATH}")
    print(f"Shape: {df.shape}")


if __name__ == "__main__":
    main()
