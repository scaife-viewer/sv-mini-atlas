@jtauber wrote:

>  remember that, for the purposes of our ingestion, the works with token-level annotations are already tokenized

(Hopefully keeping this discussion distinct from ![](https://github.trello.services/images/mini-trello-icon.png) [Spike to explore normalizing content (tokens as text parts at an exemplar level)](https://trello.com/c/BEDVmF9X)...) the token-level annotations can be roughly mapped to white-space separation of the words in the lowest text part.

For what we've done in Digital Sirah, the "values" of a token include punctuation.

```
# split on whitespace

Token
  - value # includes punctuation, e.g. οὐλομένην,
```



For the current scaife.perseus.org implementation, the `word_tokens` in the response strip out whitespace and punctuation from their values:

https://scaife.perseus.org/library/passage/urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7/json/

```
# strip whitespace and punctuation, address using offsets

Token
  - word_value # οὐλομένην
  - character-offset # 38
  - cts-string-index # 1
  - type # word
```

The offset and string index information allows us to highlight the token within the reader:

[https://scaife.perseus.org/reader/urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7/?highlight=%CE%BF%E1%BD%90%CE%BB%CE%BF%CE%BC%CE%AD%CE%BD%CE%B7%CE%BD%5B1%5D](https://scaife.perseus.org/reader/urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7/?highlight=οὐλομένην[1])



Looking at the source data for Enchiridion, I see that the source data has both a `text` value and a `word` value:

```
Token
- text_value # 	ἡμῖν,
- word_value # 	ἡμῖν
```

My thought for handling the following cards:

- ![](https://github.trello.services/images/mini-trello-icon.png) [As a reader, I want to select a text part token in the reader and update a widget that shows the token identifier](https://trello.com/c/lpomprKi)
- ![](https://github.trello.services/images/mini-trello-icon.png) [As an ATLAS consumer, I want to retrieve white-space separated tokens for a range of text parts](https://trello.com/c/VaTVeBPt)

Was that we would (at least initially) store that `text_value`

ending up with something like:

```
Token
  - TextPart (FK)
  - text
  - word
  - uuid
  - lemma
  - gloss
  - part_of_speech
  - tag
  - case
  - mood
  - named_entity

  (automatically generated)
  - idx (relative to version/exemplar)
  - position (relative to lowest text part)
```

I hadn't considered if we would want to retain the `character-offset` and

`cts-string-index` information from above (that *might* inform ![](https://github.trello.services/images/mini-trello-icon.png) [As a reader, I want the browser URL to update when I select tokens](https://trello.com/c/4wpHoqMK)); with Digital Sirah as an example, we had been passing around line idx values to refer to a particular line.  I could see a world where we could do a similar thing with a "word token" exemplar of the Iliad, so that rather than something relying on those `cts-string-index` values:

[https://scaife.perseus.org/reader/urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7/?highlight=%CE%BF%E1%BD%90%CE%BB%CE%BF%CE%BC%CE%AD%CE%BD%CE%B7%CE%BD%5B1%5D](https://scaife.perseus.org/reader/urn:cts:greekLit:tlg0012.tlg001.perseus-grc2:1.1-1.7/?highlight=οὐλομένην[1])

you could even reference a range of tokens by idx



(and even end up with a URN like `urn:cts:greekLit:tlg0012.tlg001.perseus-grc2.word_tokens:1-6` or URL like https://sv-mini.netlify.com/reader?urn=urn%3Acts%3AgreekLit%3Atlg0012.tlg001.perseus-grc2.word_tokens:%3A1-6?highlight=6)
