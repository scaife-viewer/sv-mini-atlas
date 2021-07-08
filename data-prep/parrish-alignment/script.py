import re
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
from lxml import etree

SPLITTER = re.compile(r'(?P<inner>\[{1}[^\]]+\]{1})')
MOVE_PUNCTUATION = True


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


def extract_pairs(path):
    pairs = []
    with open(path) as f:
        for line in f:
            ref, content = line.split(" ", maxsplit=1)

            found = SPLITTER.findall(content)
            iterable = SPLITTER.split(content)
            english = []
            greek = None
            records = []
            for word in iterable:
                if word.strip() not in found:
                    english_word = word.strip()
                    if MOVE_PUNCTUATION and english_word and english_word[0] in punctuation:
                        last_punc, english_word = english_word[0:1], english_word[1:]
                        english_word = english_word.strip()
                        try:
                            records[-1][1][-1] = f"{records[-1][1][-1]}{last_punc}"
                        except IndexError:
                            pairs[-1][-1][1][-1] = f"{pairs[-1][-1][1][-1]}{last_punc}"
                    english.append(english_word)
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
    return pairs

# path = "/Users/jwegner/Data/development/repos/scaife-viewer/sv-mini-atlas-fresh/data/annotations/text-alignments/parish-align.txt"


def extract_from_grc(input_path, output_path):
    lines = []
    with open(input_path) as f:
        for line in f.readlines():
            if not line[0:2] == "<s":
                continue
            line = line.strip()
            if line[-4:] != "</s>":
                line = f"{line}</s>"
            lines.append(line)

    line_num = None
    text = []
    extracted_lines = []
    for line in lines:
        elem = etree.fromstring(line)
        if elem.text and elem.text.strip():
            text.append(elem.text.strip())
        for desc in elem.iterdescendants():
            if desc.tag == "lb":
                if line_num:
                    extracted = f'{line_num}. {" ".join(text)}'
                    extracted_lines.append(extracted)
                    # print(extracted)
                    text = []
                line_num = desc.attrib["n"]
                print(line_num)

            if desc.tag == "add":
                content = " ".join(([s.strip() for s in desc.itertext()]))
                text.append(f"{content}[0]")
            elif desc.text and desc.text.strip():
                text.append(desc.text.strip())

            if desc.tail and desc.tail.strip():
                text.append(desc.tail.strip())
    if text:
        extracted_lines.append(
            f'{line_num}. {" ".join(text)}'
        )

    with open(output_path, "w") as f:
        for line in extracted_lines:
            f.write(f"{line}\n")


input_path = "data-prep/parrish-alignment/iliad01.parrish.aligned.txt"
output_path = "data-prep/parrish-alignment/parish-align.txt"

extract_from_grc(input_path, output_path)

pairs = extract_pairs(output_path)

pairs_path = "data-prep/parrish-alignment/pairs.json"
json.dump(pairs, open(pairs_path, "w"), indent=2, ensure_ascii=False)

for pair in pairs:
    ref = f"1.{pair[0][0]}"[:-1]
    print(ref, end=" ")
    for fragment in pair:
        print(*fragment[1], end=" ")
    print()
