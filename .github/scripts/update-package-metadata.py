#!/usr/bin/env python3
"""Record the author and date of a Git commit in the root package.json."""

import json
import subprocess
import sys
from pathlib import Path


def update(text, values):
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("package.json root must be an object")
    decoder = json.JSONDecoder()
    start = next(i for i, char in enumerate(text) if not char.isspace())
    if text[start] != "{":
        raise ValueError("package.json root must be an object")
    pos = start + 1
    spans = {}
    while True:
        while text[pos].isspace():
            pos += 1
        if text[pos] == "}":
            break
        key, pos = decoder.raw_decode(text, pos)
        if not isinstance(key, str):
            raise ValueError("invalid object key")
        while text[pos].isspace():
            pos += 1
        if text[pos] != ":":
            raise ValueError("invalid package.json")
        pos += 1
        while text[pos].isspace():
            pos += 1
        value_start = pos
        _, pos = decoder.raw_decode(text, pos)
        if key in values:
            if key in spans:
                raise ValueError("duplicate metadata key: " + key)
            spans[key] = (value_start, pos)
        while text[pos].isspace():
            pos += 1
        if text[pos] == "}":
            break
        if text[pos] != ",":
            raise ValueError("invalid package.json")
        pos += 1

    replacements = [(a, b, json.dumps(values[key], ensure_ascii=False)) for key, (a, b) in spans.items()]
    missing = [key for key in values if key not in spans]
    if missing:
        first = start + 1
        whitespace = text[first:next((i for i in range(first, len(text)) if not text[i].isspace()), len(text))]
        newline = "\r\n" if "\r\n" in whitespace else "\n"
        indent = whitespace.rsplit(newline, 1)[-1] if newline in whitespace else ""
        pretty = newline in whitespace
        separator = newline + indent if pretty else ""
        fields = ("," + separator).join(json.dumps(key) + (": " if pretty else ":") + json.dumps(values[key], ensure_ascii=False) for key in missing)
        existing = bool(data)
        insertion = (separator if pretty else "") + fields + ("," if existing else "")
        replacements.append((first, first, insertion))
    for a, b, value in sorted(replacements, reverse=True):
        text = text[:a] + value + text[b:]
    json.loads(text)
    return text


def main():
    path = Path("package.json")
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("package.json contains a UTF-8 BOM")
    text = raw.decode("utf-8")
    sha = sys.argv[1]
    name, date = subprocess.check_output(
        ["git", "show", "-s", "--format=%an%n%aI", sha], text=True
    ).rstrip("\n").split("\n", 1)
    result = update(text, {"last_modified": date, "last_modifier": name})
    if result != text:
        path.write_bytes(result.encode("utf-8"))


if __name__ == "__main__":
    main()
