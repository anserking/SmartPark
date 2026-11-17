from collections.abc import Callable, Sequence
from typing import TypeVar

T = TypeVar("T")
K = TypeVar("K")


def merge_sort(values: Sequence[T], key: Callable[[T], K]) -> list[T]:
    if len(values) <= 1:
        return list(values)

    middle = len(values) // 2
    left = merge_sort(values[:middle], key)
    right = merge_sort(values[middle:], key)
    return _merge(left, right, key)


def _merge(left: list[T], right: list[T], key: Callable[[T], K]) -> list[T]:
    merged: list[T] = []
    left_index = 0
    right_index = 0

    while left_index < len(left) and right_index < len(right):
        if key(left[left_index]) <= key(right[right_index]):
            merged.append(left[left_index])
            left_index += 1
        else:
            merged.append(right[right_index])
            right_index += 1

    merged.extend(left[left_index:])
    merged.extend(right[right_index:])
    return merged
