# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.

import os
import shutil
from pathlib import Path
from typing import Generator

import matplotlib.pyplot as plt
import pytest
import torch
import torch.nn as nn
from _pytest.fixtures import SubRequest
from _pytest.monkeypatch import MonkeyPatch

import torchgeo.datasets.utils
from torchgeo.datasets import ETCI2021


def download_url(url: str, root: str, *args: str) -> None:
    shutil.copy(url, root)


class TestETCI2021:
    @pytest.fixture(params=["train", "val", "test"])
    def dataset(
        self,
        monkeypatch: Generator[MonkeyPatch, None, None],
        tmp_path: Path,
        request: SubRequest,
    ) -> ETCI2021:
        monkeypatch.setattr(  # type: ignore[attr-defined]
            torchgeo.datasets.utils, "download_url", download_url
        )
        data_dir = os.path.join("tests", "data", "etci2021")
        metadata = {
            "train": {
                "filename": "train.zip",
                "md5": "ebbd2e65cd10621bc2e90a230b474b8b",
                "directory": "train",
                "url": os.path.join(data_dir, "train.zip"),
            },
            "val": {
                "filename": "val_with_ref_labels.zip",
                "md5": "efdd1fe6c90f5dfd267c88b86b237c2b",
                "directory": "test",
                "url": os.path.join(data_dir, "val_with_ref_labels.zip"),
            },
            "test": {
                "filename": "test_without_ref_labels.zip",
                "md5": "bf1180143de5705fe95fa8490835d6d1",
                "directory": "test_internal",
                "url": os.path.join(data_dir, "test_without_ref_labels.zip"),
            },
        }
        monkeypatch.setattr(ETCI2021, "metadata", metadata)  # type: ignore[attr-defined]   # noqa: E501
        root = str(tmp_path)
        split = request.param
        transforms = nn.Identity()  # type: ignore[attr-defined]
        return ETCI2021(root, split, transforms, download=True, checksum=True)

    def test_getitem(self, dataset: ETCI2021) -> None:
        x = dataset[0]
        assert isinstance(x, dict)
        assert isinstance(x["image"], torch.Tensor)
        assert isinstance(x["mask"], torch.Tensor)
        assert x["image"].shape[0] == 6
        assert x["image"].shape[-2:] == x["mask"].shape[-2:]

        if dataset.split != "test":
            assert x["mask"].shape[0] == 2
        else:
            assert x["mask"].shape[0] == 1

    def test_len(self, dataset: ETCI2021) -> None:
        assert len(dataset) == 2

    def test_already_downloaded(self, dataset: ETCI2021) -> None:
        ETCI2021(root=dataset.root, download=True)

    def test_invalid_split(self) -> None:
        with pytest.raises(AssertionError):
            ETCI2021(split="foo")

    def test_not_downloaded(self, tmp_path: Path) -> None:
        with pytest.raises(RuntimeError, match="Dataset not found or corrupted."):
            ETCI2021(str(tmp_path))

    def test_plot(self, dataset: ETCI2021) -> None:
        x = dataset[0].copy()
        dataset.plot(x, suptitle="Test")
        plt.close()
        dataset.plot(x, show_titles=False)
        plt.close()
        x["prediction"] = x["mask"][0].clone()
        dataset.plot(x)
        plt.close()
