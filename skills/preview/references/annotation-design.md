# Annotation design

The picture has to work for someone who has never seen a commit.

## Rules

- **One idea per image.** Two unrelated changes on one page means two images.
- **At most about 5 marks.** More than 5 gives a warning; treat it as a sign to split.
- **Numbers tie the picture to the text.** A badge `1` on figure 2 is described as such in
  the text. Do not number what the text never mentions. Restart badge numbers in each image.
- **Say what to look at, then stop.** One mark on one element, not a box and an arrow.
  Add a `label` only when the mark alone is unclear, and keep it to two or three words.
  A sentence goes in a `callout`, and one is usually enough.
- **Show the context.** The user must recognise the page. Prefer the normal viewport to a
  tight crop, and a wide viewport to a mobile one unless the change is mobile only.
- **Reach the state the change is about.** Open the menu, fill the form, show the result.
- **Test data looks like test data**, but realistic enough to read: "Test report", not "asdf".

Where the number sits: keep the default `corner`, and set `placement` for a whole figure or spec
to stay consistent. Use another corner when the default covers something, `inside` on large blocks
where nothing around them should be covered, and `left`, `right`, `above`, `below` on tight text.

## Which mark

| Situation | Mark |
| --- | --- |
| A new control or block | `box` with `number` |
| Something small or easy to miss | `arrow` with short `text` |
| Several steps of one flow | `badge` 1, 2, 3 on each element |
| Something moved | `arrow` with `from` the old neighbour, or two figures |
| Something gone | `removed`, see below |
| A reason that needs a sentence and belongs on the picture | `callout`; two words are a `label` |
| A small compact thing, a word or an icon, among similar ones | `ellipse`; on a long or wide element, `box` |
| One word or line of text | `underline` |
| A row or passage whose content is the point | `highlight`, which leaves it readable; `box` if nothing inside matters |
| One area on a crowded page | `spotlight`, once per image, with at most a number or label besides |
| Two places that belong together, with no movement | `connector`; `arrow` when one thing points at another |

A second `callout`, or a `spotlight` with other marks around it, usually means two ideas: split the
image. A callout covers whatever lies on its side, so check that it hides nothing the text relies on,
and set `side` if it does. The line of a `connector` runs straight across what is between the two
elements: keep them close, or use numbers.

## When to use a scheme

One idea per image still applies: a scheme is for one idea that does not fit one screen. Use it for
a path of up to about 6 steps with `steps_numbers`, `links: "sequence"` and `continuous: true`, since panels otherwise
start in fresh browser contexts and lose what the last step did, for how two or three
screens lead to each other, or for the parts of a page too long to read whole, with `crop`.
Unrelated changes stay separate figures, and one change on one page needs no scheme. Keep panels
readable: a smaller `viewport` beats a smaller `panel_width`. Start an arrow at a mark with
`from_mark` only when the place it leaves from matters. In the text, say "step 2" for a panel and
"mark 1 in step 2" for a mark.

## Colours

Crimson `#E6004C` for additions and red `#C81E1E` for removals, both with a white halo, so they
stand out on light, dark and busy pages. Change the colour with `color` only when the page itself
is close to it: set it for a whole figure or spec to stay consistent, and keep it dark enough for
white text. A removal keeps its red and its dashes unless you set `color` on that mark, so it stays
distinguishable. Do not put a mark over the thing it is about: anchor it to the
thing, and the drawing stays outside the box.

## Removed things

An element that is gone from the page has no anchor. Pick one of these, in this order:

1. **The old version runs**: use `before_url` and mark the real old element with `box` in
   `before_annotations`. This is the only one that shows the thing itself.
2. **You know where it was** from the diff or the old markup: put a `removed` marker on a
   neighbour that still exists, with an `offset` to the old place. The size comes from `offset`
   when you know it. The marker claims "it was here", so do not use it if you are guessing.
3. **Neither**: describe it in words, with no image, in the report. Say that it is gone.

A removal is only claimed when you checked that the new page does not have it.

## Checking the image

Open each PNG with Read and ask: would someone who knows nothing about the change look at
the right place, in two seconds? Does the page look as a user would see it, with no error,
spinner, cookie banner or accidental empty state? Is any real name, email or key visible?
