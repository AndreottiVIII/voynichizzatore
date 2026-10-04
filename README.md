# Voynichizer (voynichizzatore)

Takes any text and a key, and writes a "Voynich-like" manuscript in EVA (the alphabet used to transliterate the Voynich
manuscript, Beinecke MS 408). With the same key, the text comes back exactly.

    python voynichizzatore.py encode text.txt --key "a long passphrase" --out manuscript.txt
    python voynichizzatore.py decode manuscript.txt --key "a long passphrase" --out text.txt
    python voynichizzatore.py empty --key "a long passphrase" --out manuscript.txt
    python voynichizzatore.py pdf manuscript.txt --out book.pdf

Requires Python 3.12 with `numpy`, `scipy`, `scikit-learn` and, for the PDF, `matplotlib` (`pip install -r requirements.txt`). Writing a manuscript
takes a couple of minutes; reading it back takes a few seconds.

## What you get

- A whole book of 207 pages and about 4,200 lines, whatever the length of the text; one line of the file per line of
  the manuscript, `<page.line> words.separated.by.dots`, with `@` in front of the lines that open a paragraph.
- The manuscript is EVA text. The `pdf` command then writes it out as a book, one page per page, in a Voynich-like
  script: the font `VoynichizzatoreEVA.ttf` was drawn for this project by a program (`carattere.py`), stroke by stroke;
  it imitates the shapes of the Voynich signs and is not a copy of any existing font. The PDF has text only, no drawings.
- It holds between about 80,000 and 85,000 bits depending on the key, i.e. roughly 20,000 characters of text after compression. If the text is longer, the
  program says so. If it is shorter, the rest of the book is filled so that you cannot see where the message ends.

## How it works, briefly

- **The words of each page** come from the lexicon of the corresponding section of the Voynich, with a preference for
  certain glyphs (the "character" of the page) borrowed from another page; in addition there are new words, invented
  with the shape of the words that occur only once in the Voynich.
- **The message** (compressed and encrypted with the key) decides how many times each known word appears on each page.
  There is no correspondence between the words of the manuscript and the words of the text: there is nothing to
  translate word by word.
- **The arrangement** of the words in the lines follows the shape of the words (line start and end, first lines of
  paragraphs) and a few weak links between neighbouring words. It carries no information: to read the message you only
  need the words of each page and the key.
- **The layout** of each page (how many lines, how many words per line, where paragraphs start) is drawn from the
  statistics of the Voynich: no page has the layout of a real page. The words are then arranged so that the width of
  each line in characters behaves as in the Voynich, where lines with more words have shorter words.

## How close it is to the Voynich (measurements, with their limits)

Measured by hiding the same Latin text with 24 different keys. The "judges" are two classifiers that try to tell
generated pages from real ones by looking at about 220 page statistics: 0.5 means they are guessing, 1 that they never
fail.

| measure | value |
|---|---|
| judge 1 (statistics of glyphs, words, lines) | 0.55 ± 0.01 |
| judge 2 (plus: word pairs, position in the line, first lines, page profile) | 0.60 ± 0.01 |
| scorecard of 18 properties of the text (17 attainable: the Voynich itself fails one when measured the same way) | 16 |
| 8 further properties | 5 to 6 |
| lines much wider than the others on their page (over 1.5 times the median; Voynich 2.9%) | 2.8% |
| lines somewhat wider (over 1.25 times the median; Voynich 6.0%) | 11.6% |
| the text comes back exactly | 24 times out of 24 |
| wrong key rejected | 24 times out of 24 |

A manuscript with a message and one without cannot be told apart by these measures.

**What this does NOT mean.** It is not "indistinguishable from the Voynich":

- the second judge still recognises it a little (more than half of the keys give a manuscript above 0.60);
- some known properties never come out right: the width of the lines (see the table), the page profile, the spelling choices agreeing within a line as
  measured on 12 classes;
- the model was tuned on the same statistics these judges look at; a judge built independently has not been tried;
- almost all words are Voynich words: anyone who knows the program can tell that a manuscript was made with the
  program. What they cannot tell is whether there is a message inside.

## Security

- The key goes through scrypt, the text is encrypted with a SHAKE-256 stream and carries an HMAC-SHA256 tag: with the
  wrong key the program answers "wrong key".
- These are standard building blocks, but the whole **has not been reviewed by an expert**: do not use it for real
  secrets. Security depends on the key: use a long passphrase, not a dictionary word.
- Writing and reading use floating-point computations: use the same version of the program to write and to read.
  (This is v21. Manuscripts written with the previous published versions, v17 and v20, are read by this one: they
  differ only in how the words are arranged on the page, which carries no information. v21 corrects a defect of the
  earlier versions in the arrangement: the per-line counts of the spelling choices were never initialised.)
  Reading a manuscript on a computer other than the one that wrote it has not been verified yet (see the test below).

## Read-back test on another computer

    python prova.py

It reads the bundled test manuscript (written on another computer), then writes a new one and reads it back. At the
end it prints three lines: if the first says YES, a manuscript written elsewhere reads back here too.

## Sources

- **Text of the Voynich** (`voynich_zl3b.json`): from the ZL transliteration by René Zandbergen and Gabriel Landini,
  version 3b of 13 May 2025, published at https://www.voynich.nu/ , where the transliterations are stated to be in the
  public domain and are made available under the Creative Commons CC0 licence. Only the running paragraph text is
  included here, with the readable words.
- The manuscript is kept at the Beinecke Rare Book and Manuscript Library, Yale University (MS 408).

## Licence

The program is under the MIT licence (file `LICENSE`). The Voynich text in `voynich_zl3b.json` is in the public domain
(CC0). Comments in the source code are in Italian.
