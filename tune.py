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
DATA_DIR = os.environ['DATA_DIR']

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
    output_dir = os.path.join(DATA_DIR, run_name)
    os.makedirs(output_dir, exist_ok=True)
    hparams['run_name'] = run_name
    hparams['output_dir'] = output_dir

    # Save hyperparams to file with YAML
    with open(os.path.join(output_dir, 'hparams.yaml'), 'w') as f:
        yaml.dump(hparams, f)

    # Train and Validation directories
    train_dir = os.path.join(DATA_DIR, hparams['train_dir_name'])
    valid_dir = os.path.join(DATA_DIR, hparams['valid_dir_name'])
    eval_dir = os.path.join(DATA_DIR, hparams['eval_dir_name'])


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