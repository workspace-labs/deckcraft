# The content file

One JSON object. The same file makes the PowerPoint, the HTML slides and the web page.
deckcraft refuses any unknown field by name, so a typo never goes unnoticed.

```json
{
  "lang": "en",
  "title": "Northwind Freight: Q3 2026 update",
  "org": "Northwind Freight",
  "brand": {"accent": "#0055AA", "logo": "logo.png"},
  "slides": [
    {"type": "title", "eyebrow": "Q3 2026 update", "title": "Three new hubs, one faster network",
     "subtitle": "How the network changed this quarter.", "note": "Board meeting, 12 October 2026"},
    {"type": "numbers", "title": "The quarter in numbers",
     "items": [{"value": "AED 48.2M", "label": "Revenue, up 18%"}, {"value": "96.4%", "label": "On-time delivery"}]}
  ]
}
```

## Top level

| Field | Needed | What it is |
|---|---|---|
| `lang` | no | `"en"` (default) or `"ar"`. Arabic mirrors the whole layout right to left. |
| `title` | yes | The deck's name (browser tab, file properties). Up to 90 characters. |
| `org` | no | The organisation's name, shown small on every slide and in the page's top bar. Up to 40. |
| `brand` | no | `accent`: a colour like `"#0055AA"` that replaces the design's accent. `logo`: a .png or .jpg path (relative to the content file). |
| `slides` | yes | 1 to 40 slides, in order. |

## Slide types

| `type` | Needed | May have | On the web page it becomes |
|---|---|---|---|
| `title` | `title` | `eyebrow`, `subtitle`, `note` | the opening hero |
| `section` | `title` | `eyebrow`, `subtitle` | a break between parts |
| `points` | `title`, `points` (2 to 6 sentences) | `eyebrow` | a list |
| `numbers` | `title`, `items` (2 to 4 of `{"value", "label"}`) | `eyebrow` | a band of numbers |
| `chart` | `title`, `bars` (2 to 8 of `{"label", "value", "show"?}`) | `eyebrow`, `note` | a bar chart |
| `quote` | `text` | `by` | a quote |
| `closing` | `title` | `subtitle`, `contact` | the closing section; an email or web address becomes a link |

- `eyebrow` is the small line above a title ("Q3 2026 update", "Part 2"). Up to 40 characters.
- In a chart, `value` is a number (it sets the bar's height); `show` is the text above the bar
  (default: the number). The last bar is drawn in the accent colour, so put the one that matters last.
- `note` under a chart is the place for units and the source.

## Lengths

Titles up to 90 characters, subtitles 160, points 140, quotes 260, number values 20, labels 40.
Shorter is better: if a text does not fit its slide, `make` says which slide; shorten it or split it.
