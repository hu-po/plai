import os
from typing import Dict, Tuple

import torch
from torch import nn
from torch.utils.data import DataLoader, RandomSampler
from torch.optim.lr_scheduler import LambdaLR
from tqdm import tqdm

from your_module import (  # replace 'your_module' with the actual module names
    get_device,
    sam_model_registry,
    ClassyModel,
    TiledDataset,
    warmup_cosine_annealing,
    warmup_gamma,
    dice_score,
)

def train_valid(
    run_name: str = "testytest",
    output_dir: str = None,
    train_dir: str = None,
    valid_dir: str = None,
    # Model
    model: str = "vit_b",
    weights_filepath: str = "path/to/model.pth",
    freeze: bool = True,
    save_model: bool = True,
    num_channels: int = 256,
    hidden_dim1: int = 128,
    hidden_dim2: int = 64,
    dropout_prob: int = 0.2,
    # Training
    device: str = None,
    num_samples_train: int = 2,
    num_samples_valid: int = 2,
    num_epochs: int = 2,
    warmup_epochs: int = 0,
    batch_size: int = 1,
    threshold: float = 0.3,
    optimizer: str = "adam",
    lr: float = 1e-5,
    lr_sched = "cosine",
    wd: float = 1e-4,
    writer=None,
    log_images: bool = False,
    # Dataset
    curriculum: str = "1",
    resize: float = 1.0,
    interp: str = "bilinear",
    pixel_norm: bool = "mask",
    crop_size: Tuple[int] = (3, 256, 256),
    label_size: Tuple[int] = (8, 8),
    min_depth: int = 0,
    max_depth: int = 60,
    **kwargs,
):
    device = get_device(device)
    # device = "cpu"
    sam_model = sam_model_registry[model](checkpoint=weights_filepath)
    model = ClassyModel(
        image_encoder=sam_model.image_encoder,
        label_size = label_size,
        num_channels = num_channels,
        hidden_dim1 = hidden_dim1,
        hidden_dim2 = hidden_dim2,
        dropout_prob = dropout_prob,
    )
    model.train()
    if freeze:
        print("Freezing image encoder")
        for param in model.image_encoder.parameters():
            param.requires_grad = False
    model.to(device=device)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=wd)
    loss_fn = nn.BCEWithLogitsLoss()
    if lr_sched == "cosine":
        _f = lambda x: warmup_cosine_annealing(x, num_epochs, warmup_epochs, eta_min=0.1 * lr, eta_max=lr)
    elif lr_sched == "gamma":
        _f = lambda x: warmup_gamma(x, num_epochs, warmup_epochs, gamma=0.9, eta_min=0.1 * lr, eta_max=lr)
    else:
        _f = lambda x: lr
    lr_sched = LambdaLR(optimizer, _f)

    step = 0
    best_score_dict: Dict[str, float] = {}
    for epoch in range(num_epochs):
        print(f"\n\n --- Epoch {epoch+1} of {num_epochs} --- \n\n")
        for phase, data_dir, num_samples in [
            ("Train", train_dir, num_samples_train),
            ("Valid", valid_dir, num_samples_valid),
        ]:
            for _dataset_id in curriculum:
                _dataset_filepath = os.path.join(data_dir, _dataset_id)
                _score_name = f"Dice/{phase}/{_dataset_id}"
                if _score_name not in best_score_dict:
                    best_score_dict[_score_name] = 0
                _dataset = TiledDataset(
                    data_dir=_dataset_filepath,
                    crop_size=crop_size,
                    label_size=label_size,
                    resize=resize,
                    interp=interp,
                    pixel_norm=pixel_norm,
                    min_depth=min_depth,
                    max_depth=max_depth,
                    train=True,
                    device=device,
                )
                _dataloader = DataLoader(
                    dataset=_dataset,
                    batch_size=batch_size,
                    sampler = RandomSampler(
                        _dataset,
                        num_samples=num_samples,
                        # Generator with constant seed for reproducibility during validation
                        generator=torch.Generator().manual_seed(42) if phase == "Valid" else None,
                    ),
                    pin_memory=True,
                )
                # TODO: prevent tqdm from printing on every iteration
                _loader = tqdm(_dataloader, postfix=f"{phase}/{_dataset_id}/", position=0, leave=True)
                score = 0
                print(f"{phase} on {_dataset_filepath} ...")
                for images, centerpoint, labels in _loader:
                    step += 1
                    if writer and log_images:
                        writer.add_images(f"input-images/{phase}/{_dataset_id}", images, step)
                        writer.add_images(f"input-labels/{phase}/{_dataset_id}", labels.to(dtype=torch.uint8).unsqueeze(1) * 255, step)
                    images = images.to(dtype=torch.float32, device=device)
                    labels = labels.to(dtype=torch.float32, device=device)
                    preds = model(images)
                    loss = loss_fn(preds, labels)
                    optimizer.zero_grad()
                    loss.backward()
                    optimizer.step()
                    _loss_name = f"{loss_fn.__class__.__name__}/{phase}/{_dataset_id}"
                    _loader.set_postfix_str(f"{_loss_name}: {loss.item():.4f}")
                    if writer:
                        writer.add_scalar(_loss_name, loss.item(), step)
                    with torch.no_grad():
                        preds = (torch.sigmoid(preds) > threshold).to(dtype=torch.uint8)
                        score += dice_score(preds, labels).item()
                    if writer and log_images:
                        writer.add_images(f"output-preds/{phase}/{_dataset_id}", preds.unsqueeze(1) * 255, step)
                score /= len(_dataloader)
                if writer:
                    writer.add_scalar(f"Dice/{phase}/{_dataset_id}", score, step)
                # Overwrite best score if it is better
                if score > best_score_dict[_score_name]:
                    print(f"New best score! {score:.4f} ")
                    print(f"(was {best_score_dict[_score_name]:.4f})")
                    best_score_dict[_score_name] = score
                    if save_model:
                        _model_filepath = os.path.join(
                            output_dir,
                            f"model.pth")
                            #  f"model_{run_name}_best_{_dataset_id}.pth")
                        print(f"Saving model to {_model_filepath}")
                        torch.save(model.state_dict(), _model_filepath)
                # Flush ever batch
                writer.flush()
    return best_score_dict