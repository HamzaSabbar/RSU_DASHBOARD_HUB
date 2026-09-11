# Product Specification — Single Interactive RSU KPI Dashboard

## 1. Product scope

The product is a single web application:
**Dashboard de pilotage des processus du RSU**.

No dashboard hub. No dashboard selection. No separate legacy dashboard pages.

The dashboard is the product.

## 2. Primary user goals

A user must be able to:
- see the current state of RSU process performance;
- filter the KPI view by available dimensions;
- move between process families without leaving the dashboard product;
- inspect trends and breakdowns;
- upload newer KPI data;
- preview validation/import effects;
- persist the import;
- immediately see updated KPI values.

## 3. Single-dashboard information architecture

Sidebar / internal navigation:

1. Vue d’ensemble
2. Accès
3. Inscription
4. Fiabilisation des sources
5. Mise à jour & rescoring
6. Notification
7. Recours & réclamations
8. Contrôle qualité
9. Ajouter des données

“Ajouter des données” is an internal product flow (dialog/drawer/section), not another dashboard.

## 4. KPI grouping

### Accès
- ACC-01

### Inscription
- INS-01
- INS-02
- INS-03

### Fiabilisation des sources
- FSC-01

### Mise à jour & rescoring
- MAJ-01
- MAJ-02
- MAJ-03
- MAJ-04

### Notification
- NOT-01
- NOT-02

### Recours & réclamations
- REC-01
- REC-02
- REC-03
- REC-04
- REC-05

### Contrôle qualité
- CQD-01
- CQD-02

## 5. Global filters

Always visible near the dashboard top:
- Période
- Région
- Province / Préfecture
- Milieu

Rules:
- Province is dependent on selected Region.
- A global filter only applies to a KPI when that dimension exists for that KPI.
- A KPI must not disappear simply because another KPI supports more dimensions.
- The UI must make filter scope understandable.

## 6. KPI-specific filters

Use only where supported:
- canal
- genre
- tranche d’âge
- type de mise à jour
- standard / non standard
- motif du recours
- motif de réclamation
- source administrative
- type de flux
- champ contrôlé
- type d’incohérence
- type de courrier
- règle/source de suspicion
- type de fraude

CQD-02's rouge/orange/total are three parallel measures on its own card and
breakdowns (like ACC-01's 30j/90j), not a filterable dimension — no
`niveau_urgence` filter exists.

## 7. Overview

Product decision (overrides the original "compact pilot-signal subset"
guidance below): the overview must show all 18 KPIs as compact cards, not a
curated subset.

Original guidance, kept for context only (the REC-03/REC-07 named in the
original example below are the *original* 22-KPI codes, both since retired —
that REC-07's "in progress" stock concept moved into what is, after the
subsequent renumbering, today's REC-04's "en cours" column; today's REC-03 is
a different KPI, the renumbered former REC-04, "part des recours acceptés"):
> Do not render 22 equal giant cards. The overview should surface a compact
> set of pilot signals, for example: ACC-01 conversion 90j, INS-01
> aboutissement 90j, INS-02 median national inscription, MAJ-02 stock MAJ,
> MAJ-04 non-rescored households, REC-03 households with recourse <=60j,
> REC-07 complaints in progress, CQD-02 suspected households.

Also show navigation/status summaries for the seven KPI families.

## 8. KPI visualization intent

### ACC-01
- cards 30j / 90j
- monthly trend
- territorial comparison

### INS-01
- cards 30j / 60j / 90j
- multi-series monthly trend
- channel / territorial comparison

### INS-02
- national median / P75 / P90
- national trend
- available subgroup table/chart
- unsupported filtered percentile aggregation must be marked unavailable

### INS-03
- global incoherence rate
- quarterly evolution
- by controlled field
- by incoherence type

### FSC-01
- mean / median / P90
- comparison by administrative source
- trend

### MAJ-01
- national median / P75 / P90
- trend
- type / channel / complexity breakdown

### MAJ-02
- current stock
- monthly delta
- stock trend
- type / channel breakdown

### MAJ-03
- monthly initiated volume
- delta
- trend

### MAJ-04
- non-rescored rate
- trend
- territory comparison

### NOT-01
- combined activity rate (OTP réussi OR notification reçue, via the
  workbook's own precomputed union column — never OTP + notifications summed)
- trend
- age and gender breakdowns
- OTP réussi / notification reçue as secondary counts below the combined rate

### NOT-02
- delivery rate
- delivered / not delivered / in transit
- non-delivery reason

### REC-01
- weighted mean treatment delay
- delay by motive
- territory comparison

### REC-02
- open recourse stock
- trend
- motive / territory breakdown

### REC-03
- accepted recourse share
- by motive
- territory comparison

### REC-04
- weighted mean complaint treatment delay
- Portail vs CSC
- territory comparison
- "clôturés" / "en cours" counts (absorbs the original REC-07's retired in-progress stock view; "en cours" is a plain snapshot count, no trend)
- trend

### REC-05
- complaints / monthly activity ratio
- trend
- territory comparison
- underlying complaint/pre-registration/update volumes

### CQD-01
- confirmed fraud rate
- source/rule
- fraud type
- territory
- in-progress suspicions count

### CQD-02
- rouge/orange/total as three parallel measures on one card + chart (same pattern as ACC-01's 30j/90j)
- trend
- territory comparison (each région/province/milieu breakdown item carries all three measures — a stacked rouge/orange/total-by-région view falls out of this for free)

## 9. Data import UX

Inside the dashboard:
- “Ajouter des données” action;
- drag/drop or file picker for `.xlsx`;
- validate before persistence;
- preview:
  - recognized sheets;
  - rows read;
  - rows to add;
  - rows to update;
  - unchanged rows;
  - errors;
  - warnings;
  - date coverage;
- explicit confirm import button;
- post-import success summary;
- refresh/revalidate dashboard data.

Invalid files must never partially mutate the persistent dataset.

## 10. Responsive behavior

Desktop:
- persistent left sidebar;
- dense analytical layout.

Mobile/tablet:
- compact header/menu;
- filters wrap or open in a filter control;
- cards and charts stack;
- tables may use local horizontal scrolling;
- no page-level horizontal overflow.

## 11. Out of scope

Unless required by the final dashboard:
- multi-dashboard hub;
- legacy macro-national product;
- social-programs/rescoring product;
- old reporting jobs;
- old FMS/ASD/AMO/budget workflows;
- generic admin console;
- unrelated dataset-management screens.
