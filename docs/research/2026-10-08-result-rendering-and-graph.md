# Result rendering and ontology explorer

User steering: evaluate Blume for result Markdown; use React Flow and ELK for ontology. Preserve approved graph-search/content-first implementation and final full UI/backend gates.

## Blume compatibility

[Introduction](https://useblume.dev/docs), [customization](https://useblume.dev/docs/configuration/customization), [syntax](https://useblume.dev/docs/content/syntax), [components](https://useblume.dev/docs/content/components), [islands](https://useblume.dev/docs/content/islands), [custom pages](https://useblume.dev/docs/advanced/custom-pages), [content sources](https://useblume.dev/docs/content/sources) and [remote MDX](https://useblume.dev/docs/content/sources/remote-mdx) reviewed for implementation fit. Official complete documentation fetched from llms-full.txt; English documentation section inventory below includes subpages.

Blume generates an Astro/Vite documentation site. Its component overrides are statically analyzed, Astro components/layout slots, and hydrated React islands. Content sources run at build time. This is not a documented drop-in React runtime renderer for dynamically retrieved, permission-scoped content in Next.js. Do not replace app framework merely to render source passages. User said “may use”; adoption is conditional on compatibility. Task7 should provide common reading features: headings/section links, GFM tables, lists, code/copy, readable blockquotes, responsive outline, accessible citations. Render untrusted source/LLM content as Markdown without evaluating MDX, raw HTML, or arbitrary component imports. Native product citations must remain source-handle actions.

## Graph implementation

Use [React Flow](https://reactflow.dev/examples/layout/elkjs) (@xyflow/react) for interactions and elkjs layered asynchronous layout, with horizontal/vertical direction. Nodes/edges preserve RDF identifiers and predicates; no invented relationships from layout. Nodes open actual content with a separate context panel. Search/focus, domain/type/relation filters, fit/zoom controls, minimap, selected-neighborhood and evidence-path highlighting, reset and accessible list fallback. Layout errors show a usable fallback; discard stale layout responses and defer expensive layout to bounded graph changes, not every selection. Memoize node components and callbacks per [performance guidance](https://reactflow.dev/learn/advanced-use/performance); preserve [keyboard and screen-reader support](https://reactflow.dev/learn/advanced-use/accessibility). Do not enable graph mutation by connecting/deleting unless authorized via existing governance API.

Task7 gates: cyclic/disconnected/empty graphs; filter/reset; node opening; keyboard navigation; async-layout failure; 1440/768/390 viewport; reduced motion; no extra answer POSTs; graph bounded server retrieval for scale.

## Official English documentation section inventory

- [docs](https://useblume.dev/docs): Why Blume exists, What makes Blume different, Everything included, How it works, Next steps
- [blog](https://useblume.dev/docs/advanced/blog): Write a post, The RSS feed, Structured data, Building an index
- [changelog](https://useblume.dev/docs/advanced/changelog): Write an entry, The index page, From GitHub Releases, Keep entries out of the sidebar, The RSS feed, Structured data
- [custom-pages](https://useblume.dev/docs/advanced/custom-pages): Add a page, Files and routes, Reading site data, Runtime helpers, Using the site layout, 404 page, Interactive pages
- [skills](https://useblume.dev/docs/advanced/skills): Blume, Migration, Self-updating docs, Writing your site's skill
- [cli](https://useblume.dev/docs/cli): Commands, Common flags, Verifying while the dev server runs, Type-checking
- [audit](https://useblume.dev/docs/cli/audit): Flags, Failing CI, Checking a live deployment, Fixing the findings with an agent, What it does and doesn't check, Check catalog
- [doctor](https://useblume.dev/docs/cli/doctor): What it checks, The summary, Exit code and JSON
- [evals](https://useblume.dev/docs/cli/evals): How it works, Writing evals, Failing CI, Fixing the findings, Flags
- [translate](https://useblume.dev/docs/cli/translate): How it works, What gets translated, Validation, Failing CI, Limitations, Flags
- [validate](https://useblume.dev/docs/cli/validate): What counts as a page, Flags, Diagnostics, JSON output
- [version](https://useblume.dev/docs/cli/version): Listing versions, Flags, When it refuses
- [configuration](https://useblume.dev/docs/configuration): A complete example, Site, Content, Images, Frontmatter, GitHub, Last modified, Date format, SEO and agents, Table of contents, Page feedback, Feature options, Precedence
- [analytics](https://useblume.dev/docs/configuration/analytics): Adapters, PostHog, Vercel Web Analytics, Cloudflare Web Analytics, Google Analytics 4, Google Tag Manager, Plausible, Clics, Fathom, Pirsch, Databuddy, OneDollarStats, Mixpanel, Amplitude, Segment, Hightouch, Heap, Hotjar, Microsoft Clarity, LogRocket, Clearbit, Adobe Analytics, Custom scripts, Options, Custom events
- [assistant](https://useblume.dev/docs/configuration/assistant): Suggested questions, Asking about code, Contact support, Custom instructions, Grounding, Searching and reading pages, Retrieval size, External endpoint, Cross-origin callers, Server output required, Adapters, Reasoning, Analytics, Rate limiting, Bot protection
- [consent](https://useblume.dev/docs/configuration/consent): Adapters, Blume's banner, Osano, Ethyca, Changing an answer, Your own scripts
- [customization](https://useblume.dev/docs/configuration/customization): Component overrides, Layout slots, Interactive islands, Custom pages, Registry, Astro integrations, Eject
- [export](https://useblume.dev/docs/configuration/export): Enable it, PDF, EPUB, What gets exported
- [narration](https://useblume.dev/docs/configuration/narration): What it reads, Listening, Browser voices, Generated voices, Languages, Turning it off for a page, Keeping content out, Analytics
- [rate-limiting](https://useblume.dev/docs/configuration/rate-limiting): Where the count lives, Behind a reverse proxy, Turning it off
- [search](https://useblume.dev/docs/configuration/search): Using search, Popular pages, What's indexed, Tags, Ranking, Search analytics, Adapters, Excluding pages
- [theming](https://useblume.dev/docs/configuration/theming): Config tokens, theme.css, Tailwind utilities, Cascade order
- [content](https://useblume.dev/docs/content): Markdown and MDX, Files and routes, Ordering with numeric prefixes, Group folders, Drafts, Content types, Feeds, On this page, Where to next
- [components](https://useblume.dev/docs/content/components): Card and CardGroup, Steps, Tabs, View, Install the client, Install the client, Callout, Badge, Icon, File tree, Accordion, Expandable, Columns, CodeGroup, Frame, YouTube, Color, Tree, Panel, Tooltip, Tile, Prompt, Visibility, Type tables, API fields, GitHub info, Component, CodeBlock, Diff
- [frontmatter](https://useblume.dev/docs/content/frontmatter): Layout, Related pages, Sidebar, SEO, Search, AI, Changelog, Custom keys
- [i18n](https://useblume.dev/docs/content/i18n): Enable it, Organize translated content, Default-locale URLs, Per-locale navigation, Fallbacks, Links across locales, Translating with an agent, The language switcher, Routing by browser language, Translated UI, SEO, Search, Right-to-left, Where to next
- [includes](https://useblume.dev/docs/content/includes): Partials, Props, Including code files, Rules and diagnostics
- [islands](https://useblume.dev/docs/content/islands): The `islands/` convention, Registering islands in `components.ts`, Hydration, Frameworks, Hooks
- [meta](https://useblume.dev/docs/content/meta): Defining meta, Fields, Generated groups, Computed meta, Ordering within a group, Internationalization, Where to next
- [navigation](https://useblume.dev/docs/content/navigation): The generated sidebar, Page label, icon, and badge, Folder groups, Display modes, Directory listings, Ordering, Hidden pages, Tabs, Selectors, Featured links, Explicit sidebar, Header actions, Repository link, Breadcrumbs and pagination, On this page, Page actions
- [sources](https://useblume.dev/docs/content/sources): The default, Adapters, Caching and offline builds, Preview and sync, Rendering and escaping
- [contentful](https://useblume.dev/docs/content/sources/contentful): 
- [custom](https://useblume.dev/docs/content/sources/custom): 
- [github-releases](https://useblume.dev/docs/content/sources/github-releases): 
- [notion](https://useblume.dev/docs/content/sources/notion): Writing MDX in Notion
- [obsidian](https://useblume.dev/docs/content/sources/obsidian): 
- [payload](https://useblume.dev/docs/content/sources/payload): 
- [remote-mdx](https://useblume.dev/docs/content/sources/remote-mdx): 
- [sanity](https://useblume.dev/docs/content/sources/sanity): 
- [strapi](https://useblume.dev/docs/content/sources/strapi): 
- [syntax](https://useblume.dev/docs/content/syntax): Headings, Section, Getting started [#setup], Getting started \{#setup\}, Getting started <a id="setup"></a>, Appears on the page only [!toc], Appears in the TOC only [toc], Both markers together [toc] [#custom-id], Emphasis, Keyboard keys, Superscript and subscript, Blockquotes, Lists, Tables, Links and images, Horizontal rule, Code blocks, Package install, Diagrams, Callouts, Math, Smart punctuation, Syntax from other tools
- [variables](https://useblume.dev/docs/content/variables): What's new in {{version}}, Where they apply, Undefined names
- [versioning](https://useblume.dev/docs/content/versioning): Enable it, Cut a version, The switcher and the notice, SEO, Search, Agents, With i18n, What stays unversioned
- [deployment](https://useblume.dev/docs/deployment): Deploy anywhere (static), Preview locally, Subpath deploys, Mount the docs under a path, Server rendering, Private docs, Redirects, Content types, Powered-by header, Environment variables, Build cache, Build summary
- [discoverability](https://useblume.dev/docs/discoverability): What the build emits, Checking your work
- [agent-discovery](https://useblume.dev/docs/discoverability/agent-discovery): Agent readability, Discovery Link header, API catalog, AI catalog, WebMCP, Your site's skill, Skills discovery, DNS-based discovery (DNS-AID), Web Bot Auth
- [json-api](https://useblume.dev/docs/discoverability/json-api): Errors, OpenAPI description, Turning it off
- [llms-txt](https://useblume.dev/docs/discoverability/llms-txt): Options, Generated sections, Excluding a page, Bringing your own
- [markdown](https://useblume.dev/docs/discoverability/markdown): Raw Markdown, Copy as Markdown, Open in chat
- [mcp](https://useblume.dev/docs/discoverability/mcp): Tools and resources, Scoping by content type and facets, Connect to MCP menu, Server output required
- [metadata](https://useblume.dev/docs/discoverability/metadata): X attribution, Your own tags, Per-page overrides
- [open-graph](https://useblume.dev/docs/discoverability/open-graph): Brand the generated card, Show, hide, or override card layers, Card fonts, Card cache, Custom page titles
- [rss](https://useblume.dev/docs/discoverability/rss): 
- [sitemap-and-robots](https://useblume.dev/docs/discoverability/sitemap-and-robots): Sitemap, Robots
- [structured-data](https://useblume.dev/docs/discoverability/structured-data): Site identity, Custom pages
- [faq](https://useblume.dev/docs/faq): How is Blume different from Mintlify, Fumadocs, and others?, Is Blume free and open-source?, Do I need to know Astro, React, or Tailwind?, Can I use React components and MDX?, Where can I deploy it?, Does search need a hosted service?, How do I customize the look?, Why is oxfmt / Ultracite collapsing my directives?, Why does Knip report my `blume.config.ts` dependencies as unused?
- [migrating](https://useblume.dev/docs/migrating): Migrate with one command, Sources, What the agent does, Other agents, Compare first
- [quickstart](https://useblume.dev/docs/quickstart): Install and run, Write your first page, Next steps
- [api-pages](https://useblume.dev/docs/references/api-pages): The playground and samples, Site defaults
- [asyncapi](https://useblume.dev/docs/references/asyncapi): Spec versions, Code samples, Shared options, Embedding Scalar instead, Try it for events
- [graphql](https://useblume.dev/docs/references/graphql): Generated examples, Type pages, Multiple schemas, Try it playground
- [openapi](https://useblume.dev/docs/references/openapi): A local spec, OpenAPI 3.2, Route, Code samples and schemas, Try it playground, Multiple specs, Overlays, Authorization, Webhooks and callbacks, Spec warnings, Operations in your own pages, Embedding Scalar instead
- [scalar](https://useblume.dev/docs/references/scalar): What the embed doesn't do, Passing Scalar options, AsyncAPI documents
- [upgrading](https://useblume.dev/docs/upgrading): Upgrade with one command, Search, Deployment, Content sources, API references, Analytics, Assistant, Agents and other config moves, Frontmatter, Component overrides, Ejected apps, Command-line flags, Check your work
