from typing import ParamSpec, TypeVar, Callable
from functools import wraps


P = ParamSpec("P")
R = TypeVar("R")

def strict(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> Callable[P, R]:
        param_types  = tuple([
            value for key, value in func.__annotations__.items()
            if key != "return"
        ])

        args_ok = [isinstance(a, param_types) for a in args]
        kwargs_ok = [isinstance(v, param_types) for v in kwargs.values()]

        if not all(args_ok) or not all(kwargs_ok):
            raise TypeError(
                "Некорректные типы аргументов для функции "
                f"{func.__name__}: {args} {kwargs}"
            )
        return func(*args, **kwargs)
    return wrapper


@strict
def sum_two(a: int, b: int) -> int:
    return a + b


tests = [
    {
        'args': (3, 7),
        'kwargs': {},
        'answer': 10,
    },
    {
        'args': (),
        'kwargs': {'a': 12, 'b': 8},
        'answer': 20,
    },
    {
        'args': (1, '2'),
        'kwargs': {},
        'raises': TypeError,
    },
    {
        'args': (1.5, 2),
        'kwargs': {},
        'raises': TypeError,
    },
]


if __name__ == "__main__":
    for i, test in enumerate(tests, 1):
        print(i, test)
        if 'raises' in test:
            try:
                sum_two(*test['args'], **test['kwargs'])
            except test['raises']:
                print(f'Test {i}: OK (исключение {test["raises"].__name__})')
            else:
                raise AssertionError(f'Test {i}: не возникло {test["raises"].__name__}')
        else:
            result = sum_two(*test['args'], **test['kwargs'])
            assert result == test['answer'], f'Test {i}: {result=} != {test["answer"]=}'
            print(f'Test {i}: OK (результат {result})')
