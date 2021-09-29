## Basic Config
```python
from dataclass_config import Config

default_config = Config()

@default_config('optimizer')
class OptimizerConfig:
    lr: float = 1e-3
    weight_decay: float = 0

@default_config('training')
class TrainingConfig:
    epochs: int = 100
    batch_size: int = 512

print(default_config.optimizer.lr)
print(default_config.optimizer.weight_decay)
print(default_config.training.epochs)
print(default_config.training.batch_size)

print(default_config.asdict())
```

## Overriding Default Config
```python
from dataclass_config import Config

config = Config(default_config)

@config('optimizer')
class OptimizerConfig:
    lr: float = 1e-2

print(config.optimizer.lr)
print(config.optimizer.weight_decay)
print(config.training.epochs)
print(config.training.batch_size)

print(config.asdict())
```

## Command Line Arguments
```python
from typing import List
from dataclass_config import Config, Argument

config = Config(default_config)

@config('training')
class TrainingConfig:
    epochs: Argument[int] = Argument()
    seeds: Argument[List[int]] = Argument()
    cuda: Argument[bool] = Argument(False)

args = config.parse_args()

print(args.optimizer.lr)
print(args.optimizer.weight_decay)
print(args.training.epochs)
print(args.training.batch_size)

print(args.asdict())

"""
$ python examples.py --help
usage: examples.py [-h] --epochs EPOCHS

optional arguments:
  -h, --help       show this help message and exit
  --epochs EPOCHS

$ python examples.py --epochs 100 --seeds 123 321 123123 321321
0.001
0
100
512
{'optimizer': {'lr': 0.001, 'weight_decay': 0}, 'training': {'epochs': 100, 'batch_size': 512, 'seeds': [123, 321, 123123, 321321], 'cuda': False}}

$ python examples.py --epochs 100 --seeds 123 321 123123 321321 --cuda
0.001
0
100
512
{'optimizer': {'lr': 0.001, 'weight_decay': 0}, 'training': {'epochs': 100, 'batch_size': 512, 'seeds': [123, 321, 123123, 321321], 'cuda': True}}
"""
```
