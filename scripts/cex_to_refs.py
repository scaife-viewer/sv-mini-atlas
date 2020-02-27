import csv
import os

path = input("Provide a file path:\n")

with open(path, "r") as source:
    output_path = f"refs-{os.path.basename(path)}"
    dest = open(output_path, "w", encoding="utf-8")
    for line in source:
        urn, content = line.strip().split("#", maxsplit=1)
        _, ref = urn.rsplit(":", maxsplit=1)
        dest.write(
            f"{ref} {content}\n"
        )
