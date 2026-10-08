# Content-first UI design implementation

The selected 12ui D concept and expanded document, dataset, and ontology screens informed the light red palette, pale tinted surfaces, Swiss typography, reading widths, and source/content/context hierarchy. Implemented-page alignment kits were generated for each of those three states at 1440 × 900 and their README and annotated plans reviewed. The frontend is under frontend/src; a hint-path error was repaired in the local kit configuration and the settled conversions reused.

The prototype is illustrative: its dates, rows, policy names, evidence arrows, and provenance are not authoritative source data. The live UI renders ContentPage contracts and scoped RDF graph results instead. This takes precedence over generic asset-copy instructions:

- Preserve the app's existing nine-dot brand and Knowledge Product Manager name; the generated interlocking-ring logo is a reference only.
- Generated graph arrows, tiny graph image, graph-node glyphs and minimap are replaced by React Flow's actual edges, nodes and minimap because the user explicitly requested an interactive RDF explorer.
- Illustrative source/product/transformation emblems are reference only: provenance must reflect the actual returned source, rather than imply an unregistered transformation.
- Invented sidebar destinations and prototype data are omitted. Existing catalog/workspace navigation and actual source fields remain.
- Preserve a single accessible dialog with source switching, content-first reading, separate context/relationships, keyboard dismissal and focus return. Desktop prototypes use side columns; the implemented tabs retain the same information on narrow screens without nested modals.
- Apply reviewed typography/color tokens to real elements; do not replace executable source content with screenshot text.

Markdown uses react-markdown with GFM and HTML skipped, no embeds/images/executable MDX, and text-only source links. Blume's Astro/Vite documentation-site framework is not a drop-in runtime renderer for this Next application; the compatibility research covers its official documentation and subpages.

Verification: actual source rows/policies, source switching, explicit store failure, hostile markup, mobile overflow, focus/Escape, aliases/node focus, source-backed paths, and opening policy clauses are browser regressions. Structured AI answers display only accepted claims, neutral sections and named locator-specific citations; clicking them uses the same authorized run and source version.
