import argparse
import os
import pprint
import shutil
import uuid

import numpy as np
import yaml
from hyperopt import fmin, hp, tpe
from tensorboardX import SummaryWriter

from src import train_valid, eval_from_episode_dir

parser = argparse.ArgumentParser()
parser.add_argument('--seed', type=int, default=DEFAULT_SEED)

DEFAULT_SEED = 0  # Replace with your default seed
OUTPUT_DIR = ""  # Replace with your data directory

# Define the search space
HYPERPARAMS = {
    'train_dir_name' : 'train',
    'valid_dir_name' : 'valid',
    'eval_dir_name' : 'valid',
    # Model
    'model_str': hp.choice('model_str', [
        'vit_b|sam_vit_b_01ec64.pth',
        # 'vit_h|sam_vit_h_4b8939.pth',
        # 'vit_l|sam_vit_l_0b3195.pth',
    ]),
    'freeze': hp.choice('freeze', [
        True,
        # False, # Uses up too much memory
    ]),
    "hidden_dim1" : hp.choice("hidden_dim1", [
        256,
        128,
        64,
    ]),
    "hidden_dim2" : hp.choice("hidden_dim2", [
        256,
        128,
        64,
    ]),
    "dropout_prob" : hp.choice("dropout_prob", [
        0.5,
        0.2,
        0,
    ]),
    # Dataset
    'threshold': hp.choice('threshold', [
        # 0.5,
        0.2,
        # 0.1,
    ]),
    'curriculum': hp.choice('curriculum', [
        '1', # Depth of 1 - 40/45
        # '2', # Depth of 1 - 53/58
        # '3', # Depth of 1 - 48/53
        # '123',
    ]),
    'num_samples_train': hp.choice('num_samples_train', [
        # 2,
        # 2000,
        # 8000,
        20000,
        # 200000,
    ]),
    'num_samples_valid': hp.choice('num_samples_valid', [
        # 2,
        200,
        # 8000,
    ]),
    'resize': hp.choice('resize', [
        1.0, # Universal Harmonics
        # 0.3,
    ]),
    'pixel_norm': hp.choice('pixel_norm', [
        "mask",
        "ink",
        "bg",
    ]),
    'crop_size_str': hp.choice('crop_size_str', [
        '256.256', # Universal Harmonics
        # '128.128',
        # '68.68',
    ]),
    'max_depth': hp.choice('max_depth', [
        42, # Universal Harmonics
    ]),
    'lr_sched': hp.choice('lr_sched', [
        # 'cosine',
        # 'gamma',
        'flat',
    ]),
    # Training
    'seed': 0,
    'batch_size' : 2,
    'num_epochs': hp.choice('num_epochs', [
        # 1,
        # 8,
        16,
    ]),
    'warmup_epochs': hp.choice('warmup_epochs', [
        0,
        1,
    ]),
    'lr': hp.loguniform('lr',np.log(0.0001), np.log(0.01)),
    'wd': hp.choice('wd', [
        1e-4,
        1e-3,
        0,
    ]),
}

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

def eval_from_episode_dir(
    episode_dir: str = None,
    eval_dir: str = None,
    output_dir: str = None,
    weights_filename: str = "model.pth",
    hparams_filename: str = "hparams.yaml",
    **kwargs,
):
    # Get hyperparams from text file
    _hparams_filepath = os.path.join(episode_dir, hparams_filename)
    with open(_hparams_filepath, "r") as f:
        hparams = yaml.load(f, Loader=yaml.FullLoader)
    _weights_filepath = os.path.join(episode_dir, weights_filename)
    # Merge kwargs with hparams, kwargs takes precedence
    hparams = {**hparams, **kwargs}
    print(f"Hyperparams:\n{pprint.pformat(hparams)}\n")
    # Make sure output dir exists
    os.makedirs(output_dir, exist_ok=True)
    eval(
        eval_dir=eval_dir,
        output_dir=output_dir,
        weights_filepath=_weights_filepath,
        **hparams,
    )

def episode(hparams) -> float:

    # Print hyperparam dict with logging
    print(f"\n\n Starting EPISODE \n\n")
    print(f"\n\nHyperparams:\n\n{pprint.pformat(hparams)}\n\n")

    # Create output directory based on run_name
    run_name: str = str(uuid.uuid4())[:8]
    output_dir = os.path.join(OUTPUT_DIR, run_name)
    os.makedirs(output_dir, exist_ok=True)

    # Train and Validation directories
    train_dir = os.path.join(DATA_DIR, hparams['train_dir_name'])
    valid_dir = os.path.join(DATA_DIR, hparams['valid_dir_name'])
    eval_dir = os.path.join(DATA_DIR, hparams['eval_dir_name'])

    # Save hyperparams to file with YAML
    with open(os.path.join(output_dir, 'hparams.yaml'), 'w') as f:
        yaml.dump(hparams, f)

    # Repurpose this to consume a string version of the arguments for an instance of the Servo class
    servo_args = hparams['servo_args_str'].split(',')
    # Example Servo object: Servo(1, "hip", (1676, 2293),"swings the robot horizontally from left to right, yaw")
    hparams['servo'] = Servo(int(servo_args[0]), servo_args[1], tuple(map(int, servo_args[2].split('-'))), servo_args[3])

    try:
        writer = SummaryWriter(logdir=output_dir)
        # Train and evaluate a TFLite model
        score_dict = train_valid(
            run_name =run_name,
            output_dir = output_dir,
            train_dir = train_dir,
            valid_dir = valid_dir,
            model=model,
            weights_filepath=weights_filepath,
            writer=writer,
            **hparams,
        )
        writer.add_hparams(hparams, score_dict)
        eval_from_episode_dir(
            eval_dir = eval_dir,
            episode_dir = output_dir,
            output_dir = output_dir,
            eval_on = hparams['curriculum'],
            max_num_samples_eval = 5000,
            max_time_hours = 0.1,
            log_images = False,
            save_pred_img = True,
            save_submit_csv = False,
            save_histograms = False,
            writer=writer,
            **hparams,
        )
        writer.close()
        # Score is average of all scores
        score = sum(score_dict.values()) / len(score_dict)
    except Exception as e:
        print(f"\n\n (ERROR) EPISODE FAILED (ERROR) \n\n")
        print(f"Potentially Bad Hyperparams:\n\n{pprint.pformat(hparams)}\n\n")
        raise e
        # print(e)
        # score = 0
    # Maximize score is minimize negative score
    return -score

if __name__ == "__main__":
    args = parser.parse_args()
    HYPERPARAMS['seed'] = args.seed
    best = fmin(
        episode,
        space=HYPERPARAMS,
        algo=tpe.suggest,
        max_evals=100,
        rstate=np.random.Generator(np.random.PCG64(args.seed)),
    )