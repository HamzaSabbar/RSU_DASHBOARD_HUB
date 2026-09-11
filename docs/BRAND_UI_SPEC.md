# RSU Brand & UI Specification

## Principle

**Do not redesign the product.**

The existing RSU visual system in the repository is the source of truth. The KPI dashboard must feel like a direct continuation of the existing RSU product, not a generic SaaS dashboard.

Inspect and preserve, where still active:
- `apps/web/tailwind.config.ts`
- `apps/web/app/globals.css`
- `apps/web/components/brand-mark.tsx`
- `apps/web/components/app-sidebar.tsx`
- generic UI Card/Badge/Table controls
- reusable KPI/chart/table patterns

## Core typography

Primary product font:
- Inter
- system-ui fallback

Do not add a new primary typeface.

The brand reference contains font resources, but the final application should use the repository’s existing approved font setup rather than copying embedded font blobs.

## Existing key color tokens

Use the repository tokens, not a new palette.

Current key product values:
- brand primary: `#0A3D2A`
- brand dark: `#062818`
- positive: `#1F8A5B`
- danger: `#D73838`
- red/darker alert: `#B32424`
- surface: `#FFFFFF`
- surface-soft: `#FAFAFA`
- background: `#FAFAF9`
- paper: `#FBFAF6`
- ink: `#14140F`
- soft ink: `#4A4A44`
- muted: `#707070`
- border: `#ECECEC`
- border strong: `#DCDCDC`

Brand reference also establishes a neutral/paper language:
- off-white paper surfaces;
- subtle gray rules;
- dark ink;
- restrained red alerts;
- green as primary semantic emphasis.

## Spacing from brand reference

Use existing components first. When new KPI layout primitives are needed, preserve:
- KPI card horizontal padding: ~24px
- KPI card vertical padding: ~24px where the existing component scale allows
- panel padding: ~24px
- section gap: ~16px

Avoid arbitrary dense/loose spacing that conflicts with the existing interface.

## Sidebar

Preserve the current product language:
- desktop fixed left sidebar;
- width approximately 240px (`w-60`);
- white surface;
- right border;
- 56px top brand/header row (`h-14`);
- compact nav rows;
- Lucide icons;
- uppercase small group labels;
- active item with restrained border/white state;
- mobile compact header.

Change the **content**, not the visual grammar.

New sidebar content:
- Vue d’ensemble
- Accès
- Inscription
- Fiabilisation des sources
- Mise à jour & rescoring
- Notification
- Recours & réclamations
- Contrôle qualité
- Ajouter des données

## BrandMark

Preserve the current BrandMark icon geometry/color language unless product naming is intentionally changed.

If the visible wordmark is renamed from legacy `rsu-hub`, modify the text only after checking stakeholder intent; keep the emblem and visual treatment consistent.

Do not replace it with an unrelated logo.

## Cards

Existing KPI card language:
- light/white card surface;
- subtle border/shadow;
- compact uppercase muted label;
- large bold value;
- green/positive/danger tones only when semantically justified;
- missing value shown explicitly, never as fake zero.

For KPI cards:
- code and title must be legible;
- values use strong numeric hierarchy;
- unit/period/context is secondary;
- delta badges must distinguish positive/negative meaning by KPI semantics, not merely by mathematical sign.

Some KPIs are “lower is better”; do not color every positive numeric delta green.

## Panels

- simple light surfaces;
- subtle borders;
- little or no decorative effects;
- consistent ~24px content padding;
- section titles compact and high contrast;
- avoid nested card-within-card excess.

## Tables

Preserve the existing compact, institutional table language:
- clear headers;
- subtle row separators;
- numeric alignment;
- sticky header where useful;
- no unnecessary zebra/color noise;
- local horizontal scroll on small screens.

## Charts

Use Recharts already in the project.

Required chart behavior:
- clear title;
- unit;
- tooltip;
- legend for multiple series;
- responsive container;
- no-data state;
- readable axes;
- restrained grid lines;
- same palette semantics across the whole product.

Visual priorities:
- RSU green for primary/current/positive series;
- dark neutral for secondary;
- red only for alert/negative/confirmed adverse concepts;
- additional series use restrained distinct tones, not rainbow colors.

Do not use:
- gradients for decoration;
- neon colors;
- glassmorphism;
- 3D charts;
- oversized rounded “bubble” UI;
- generic admin-template aesthetics.

## Inputs and filters

Use the existing small, bordered control language:
- white background;
- subtle border;
- compact height;
- brand-green focus state;
- readable label;
- consistent select/date/input styling.

Filters must visually distinguish:
- global dashboard filters;
- KPI-specific filters.

## Motion

Keep motion minimal. Existing brand reference is restrained and includes no need for decorative animation.

Use transitions only for normal interaction feedback.

## Responsive

Desktop:
- sidebar + analytical content;
- multi-column cards/charts where useful.

Mobile:
- compact top header/menu;
- stacked KPI content;
- touch-friendly controls;
- no page-level horizontal scrolling;
- table/chart local scrolling only where needed.

## Accessibility

- semantic controls;
- focus-visible states;
- WCAG-conscious contrast;
- no color-only meaning;
- chart tooltip information should have a table/label equivalent where feasible;
- keyboard-usable import flow.

## Final visual test

At completion compare the new screens against the existing RSU interface, not against a generic dashboard inspiration.

A reviewer should recognize the same RSU product family immediately.
