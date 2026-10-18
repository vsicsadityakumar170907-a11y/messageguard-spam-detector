from io import BytesIO
from pathlib import Path
from urllib.request import urlopen
from zipfile import ZipFile

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

UCI_DATA_URL = (
    "https://archive.ics.uci.edu/static/public/228/"
    "sms+spam+collection.zip"
)
INDIA_DATA_URL = (
    "https://raw.githubusercontent.com/princebari/"
    "-SMS-Spam-Classification-on-Indian-Dataset-A-Crowdsourced-"
    "Collection-of-Hindi-and-English-Messages/main/indian_spam.csv"
)

UCI_DATA_FILE = DATA_DIR / "SMSSpamCollection"
INDIA_DATA_FILE = DATA_DIR / "indian_spam_hindi_english.csv"


def download_uci_dataset():
    if not UCI_DATA_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with urlopen(UCI_DATA_URL, timeout=60) as response:
            zip_bytes = response.read()

        with ZipFile(BytesIO(zip_bytes)) as archive:
            dataset_bytes = archive.read("SMSSpamCollection")

        UCI_DATA_FILE.write_bytes(dataset_bytes)

    data = pd.read_csv(
        UCI_DATA_FILE,
        sep="\t",
        header=None,
        names=["label", "text"],
        encoding="utf-8",
    )
    data["source"] = "UCI English SMS"
    return data


def download_india_dataset():
    if not INDIA_DATA_FILE.exists():
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with urlopen(INDIA_DATA_URL, timeout=60) as response:
            csv_bytes = response.read()

        INDIA_DATA_FILE.write_bytes(csv_bytes)

    data = pd.read_csv(INDIA_DATA_FILE, encoding="utf-8-sig")

    columns = {
        str(column).strip().lower(): column
        for column in data.columns
    }

    label_column = columns.get("label") or columns.get("v1")
    message_column = (
        columns.get("msg")
        or columns.get("text")
        or columns.get("message")
        or columns.get("v2")
    )

    if label_column is None or message_column is None:
        raise ValueError(
            "Indian SMS CSV format changed. Expected label/text "
            "or v1/v2 columns."
        )

    data = data.rename(
        columns={
            label_column: "label",
            message_column: "text",
        }
    )
    data["source"] = "Indian Hindi-English SMS"
    return data[["label", "text", "source"]]


def normalize_labels(data):
    data = data.copy()
    data["label"] = data["label"].astype(str).str.strip().str.lower()

    label_map = {
        "ham": "ham",
        "legitimate": "ham",
        "not spam": "ham",
        "0": "ham",
        "spam": "spam",
        "1": "spam",
    }
    data["label"] = data["label"].map(label_map)

    data["text"] = data["text"].fillna("").astype(str).str.strip()
    data = data.dropna(subset=["label"])
    data = data[data["text"] != ""]

    return data


def load_dataset():
    """Load and combine UCI English and Indian Hindi-English SMS data."""
    uci_data = download_uci_dataset()
    india_data = download_india_dataset()

    combined = pd.concat(
        [
            uci_data[["label", "text", "source"]],
            india_data[["label", "text", "source"]],
        ],
        ignore_index=True,
    )

    combined = normalize_labels(combined)
    combined = combined.drop_duplicates(subset=["text"])
    return combined.reset_index(drop=True)