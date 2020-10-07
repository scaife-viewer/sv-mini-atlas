import os


# def main():
#     path = "/Users/jwegner/Data/development/repos/scaife-viewer/sv-mini-atlas-fresh/data/annotations/text-alignments/iliad-parish.txt"

#     lines = []
#     with open(path) as f:
#         for pos, line in enumerate(f):
#             if pos < 7:
#                 continue
#             break
#     return line

# def extract_tokens(line):
#     words = [w.strip() for w in line.split() if w]
# if __name__ == "__main__":
#     line = main()


import json
impor tre
from lxml import etree

with open("/Users/jwegner/Data/development/repos/scaife-viewer/sv-mini-atlas-fresh/data/annotations/text-alignments/iliad-parish.xml") as f:
    tree = etree.parse(f)

ns = {"text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0"}
counter = 0
lines = []
matches = tree.xpath('//text:p[@text:style-name="P6"]', namespaces=ns)
sentence_pattern = re.compile(r'\d{7}\w{0,1}')
for pos, elem in enumerate(matches):
    cleaned = " ".join([f.strip() for f in elem.itertext() if f.strip()])
    try:
        ref, content = [t.strip() for t in cleaned.split(".", maxsplit=1)]
    except:
        ref, content = [t.strip() for t in cleaned.split(" ", maxsplit=1)]
    ref = f"{ref}."
    words = []
    for word in content.split():
        if not word.strip():
            continue
        if not sentence_pattern.match(word):
            words.append(word)
    if ref.startswith("["):
        break
    print(ref, *words)

splitter = re.compile(r'(?P<inner>\[{1}[^\]]+\]{1})')

pairs = []
with open("/Users/jwegner/Data/development/repos/scaife-viewer/sv-mini-atlas-fresh/data/annotations/text-alignments/parish-align.txt") as f:
    for line in f:
        ref, content = line.split(" ", maxsplit=1)

        found = splitter.findall(content)
        iterable = splitter.split(content)
        english = []
        greek = None
        records = []
        for word in iterable:
            if word.strip() not in found:
                english.append(word.strip())
                continue
            else:
                greek = word.split("[", maxsplit=1)[1].rsplit(":", maxsplit=1)[-1].strip("]").split()
                if next(iter(greek), "0") == "0":
                    # we need to ingest this stuff
                    greek = []
                records.append(
                    (ref, english, greek)
                )
                if len(greek) > 1:
                    print(line)
                # else could retain greek if need be
                # also need to check for unmapped english; equivalent of "0" for greek
                english = []
        pairs.append(records)

json.dump(pairs, open("pairs.json", "w"), indent=2, ensure_ascii=False)

for pair in pairs:
    ref = f"1.{pair[0][0]}"[:-1]
    print(pair[0][0], end=" ")
    for fragment in pair:
        print(*fragment[1], end=" ")
    print()
