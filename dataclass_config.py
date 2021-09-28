from dataclasses import dataclass, fields, asdict, make_dataclass, field
from typing import TypeVar, Generic, Union, List, get_origin, get_args, Optional
import argparse
from itertools import chain
from collections import abc, defaultdict
from functools import singledispatch


T = TypeVar('T')


def get_origins_and_arg(tp):
    origins = []

    def _get_args(tp):
        args = get_args(tp)
        if args:
            origin = get_origin(tp)
            if origin:
                origins.append(origin)
            tp, _ = _get_args(args[0])
        return tp, origins
    return _get_args(tp)


class Required(Generic[T]):
    pass


class RequiredError(Exception):
    pass


def check_required(config, raise_error=True):
    is_required, loc = _check_required(config, [])
    if is_required and raise_error:
        raise RequiredError(f"{'.'.join(reversed(loc))} is required!")
    return is_required, loc


@singledispatch
def _check_required(obj, loc):
    return False, loc


@_check_required.register
def _check_required_tuple(obj: tuple, loc):
    # Assume tuples are key and values
    is_required, loc = _check_required(obj[1], loc)
    if len(obj) > 1 and is_required:
        loc.append(obj[0])
    return is_required, loc


@_check_required.register
def _check_required_map(obj: abc.Mapping, loc):
    return _check_required(list(obj.items()), loc)


@_check_required.register
def _check_required_str(obj: str, loc):
    return False, loc


@_check_required.register
def _check_required_seq(obj: abc.Sequence, loc):
    for value in obj:
        is_required, loc = _check_required(value, loc)
        if is_required:
            return True, loc
    return False, loc


@_check_required.register
def _check_required_req(obj: Required, loc):
    return True, loc


@dataclass(frozen=True)
class Argument(Generic[T]):
    default: Union[T, Required] = Required()
    additional_flags: List[str] = field(default_factory=list)
    help: str = ''
    metavar: Optional[str] = None


@dataclass(frozen=True)
class Choice(Generic[T]):
    choices: List[T]
    default: Union[T, Required] = Required()


class dotdict(dict):
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__  # type: ignore
    __delattr__ = dict.__delitem__  # type: ignore


class Config:
    def __init__(self, config=None):
        if config is not None:
            if isinstance(config, Config):
                self.configs = config.configs
            else:
                self.configs = config
        else:
            self.configs = dotdict()
        self.parser = None

    def add(self, name):
        if name in self.configs:
            def _dataclass(cls):
                cls_dataclass = dataclass(cls)
                data = cls_dataclass()
                dict = {}
                for f in chain(fields(self.configs[name]), fields(data)):
                    dict[f.name] = (f.name, f.type, f)
                new_dataclass = make_dataclass(cls.__name__, dict.values())
                self.configs[name] = new_dataclass()
                return new_dataclass
        else:
            def _dataclass(cls):
                cls_dataclass = dataclass(cls)
                self.configs[name] = cls_dataclass()
                return cls_dataclass
        return _dataclass

    def __getattr__(self, name):
        return self[name]

    def __getitem__(self, name):
        return self.configs[name]

    def __call__(self, name):
        return self.add(name)

    def __iter__(self):
        yield from self.configs.items()

    def asdict(self):
        dict = dotdict()
        for name, config in self.configs.items():
            dict[name] = asdict(config, dict_factory=dotdict)
        return dict

    def __str__(self):
        return str(self.configs)

    def parse_args(self):
        loc = defaultdict(default_factory={})
        for name, config in self.configs.items():
            for f in fields(config):
                value = f.default
                if not isinstance(value, Argument):
                    continue

                loc[f.name] = name
                if self.parser is None:
                    self.parser = argparse.ArgumentParser()
                type, origins = get_origins_and_arg(f.type)
                kwargs = {'help': value.help}
                if type is bool:
                    if isinstance(value.default, Required):
                        raise ValueError('Type bool can not be required!')
                    # Register bool argument as an action
                    kwargs['action'] = f'store_{str(not bool(value.default)).lower()}'
                    kwargs['dest'] = f.name
                    self.parser.set_defaults(**{f.name: bool(value.default)})
                else:
                    kwargs['type'] = type
                    kwargs['metavar'] = value.metavar

                # Check required
                if (isinstance(value.default, Required) or
                        (isinstance(value.default, Choice) and
                            isinstance(value.default.default, Required))):
                    kwargs['required'] = True

                # Choices
                if isinstance(value.default, Choice):
                    kwargs['default'] = value.default.default
                    kwargs['choices'] = value.default.choices
                else:
                    kwargs['default'] = value.default

                # List
                if origins and origins[-1] is list:
                    kwargs['nargs'] = '+'

                self.parser.add_argument(
                    f'--{f.name}', *value.additional_flags, **kwargs)

        # Parse arguments and update the config
        config = self.asdict()
        if self.parser:
            for key, value in vars(self.parser.parse_known_args()[0]).items():
                config[loc[key]][key] = value
        return Config(config)


@_check_required.register
def _check_required_config(obj: Config, loc):
    return _check_required(obj.asdict(), loc)
