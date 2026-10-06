# 0007. Authoring app shell

Date: 2026-10-06

## Status

Accepted

## Context

Codify's web surfaces (`codify-web` and the Pages site) were a single
scrolling page with a top header. Declutter slices (#21–#23) reduced copy
and switched the palette to indigo on cool gray, but the information
architecture stayed "one page, two view tabs".

The product job is still clause → control statement → review/accept →
OSCAL catalog ([ADR 0006](0006-clause-only-input.md) for input;
[ADR 0002](0002-oscal-1-1-2.md) for the catalog). Reviewers asked for a
real authoring app: a Linear-style shell (sidebar, list, writing column,
properties) without copying Linear branding, and without new outbound
origins ([ADR 0003](0003-local-only-privacy-model.md)).

A follow-on slice adds a risk register in the same shell. The shell has to
leave a place for it without reversing clause-only input.

## Decision

The local web app and the Pages site share one **authoring app shell**:

- A collapsible left sidebar for navigation: Workspace, Clauses, Risks,
  Catalog, Export, Guide.
- A top bar with a breadcrumb and the primary export action.
- A centred writing column for the control statement.
- A right properties and review panel.

Workspace with no project is still clause-text start (paste / open file /
example). Clauses is the list + editor. Catalog lists controls with a
source column. Export is a dialog of download targets, not a second save
format. Risks in this decision is a nav destination; its data model is a
later ADR.

Static assets stay four files (`index.html`, `app.css`, `app.js`,
`theme.js`) copied by `scripts/build_site.py`. We do not split `static/`
into a bundler graph in this slice.

Light / dark / system theming, the system font stack, and CSP `connect-src`
do not change.

## Consequences

- e2e selectors move from a top `nav.views` to the sidebar and from a
  split export button to the export dialog.
- Clause and control numbers stay off the list ([ADR 0006](0006-clause-only-input.md));
  the properties panel may show the internal control id for export and
  resume.
- A later risk slice fills the Risks destination and the Catalog source
  column. It must not add a Title field or make clause numbers required.
- Splitting `app.js` into ES modules later is a new ADR, because the Pages
  build copies named files and has no bundler.
