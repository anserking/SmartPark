import unicodedata
from dataclasses import dataclass, field


@dataclass(slots=True)
class _TrieNode:
    children: dict[str, "_TrieNode"] = field(default_factory=dict)
    display_value: str | None = None


class Trie:
    def __init__(self) -> None:
        self._root = _TrieNode()
        self._size = 0

    @staticmethod
    def normalize(text: str) -> str:
        return " ".join(unicodedata.normalize("NFKC", text).casefold().split())

    def insert(self, value: str) -> None:
        display_value = value.strip()
        normalized = self.normalize(display_value)
        if not normalized:
            raise ValueError("Trie values cannot be empty")

        node = self._root
        for character in normalized:
            node = node.children.setdefault(character, _TrieNode())
        if node.display_value is None:
            self._size += 1
            node.display_value = display_value

    def prefix_search(self, prefix: str, limit: int = 10) -> list[str]:
        if limit <= 0:
            raise ValueError("Suggestion limit must be positive")

        normalized = self.normalize(prefix)
        if not normalized:
            return []

        node = self._root
        for character in normalized:
            child = node.children.get(character)
            if child is None:
                return []
            node = child

        suggestions: list[str] = []
        self._collect(node, suggestions, limit)
        return suggestions

    @property
    def size(self) -> int:
        return self._size

    @classmethod
    def _collect(cls, node: _TrieNode, output: list[str], limit: int) -> None:
        if node.display_value is not None:
            output.append(node.display_value)
            if len(output) >= limit:
                return

        for character in sorted(node.children):
            cls._collect(node.children[character], output, limit)
            if len(output) >= limit:
                return
