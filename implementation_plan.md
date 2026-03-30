# Fix Technical SEO for Location Pages

Fix technical SEO issues across 3 location pages ([limassol-jewelry-store.html](file:///C:/Users/mar1/.gemini/antigravity/scratch/niassets/limassol-jewelry-store.html), [nicosia-jewelry-old-town.html](file:///C:/Users/mar1/.gemini/antigravity/scratch/niassets/nicosia-jewelry-old-town.html), [nicosia-jewelry-store.html](file:///C:/Users/mar1/.gemini/antigravity/scratch/niassets/nicosia-jewelry-store.html)) in the Tahiti18/niassets repo. No copy changes—only structural/technical fixes.

## Audit Results

| Check | Status | Notes |
|---|---|---|
| Google Maps iframe | ⚠️ FIX | All 3 have fabricated place IDs (`0x1234567890abcdef`) |
| JSON-LD JewelryStore schema | ✅ Present | Missing `description` and `hasMap` |
| Phone `tel:` clickable | ✅ OK | All correct |
| Get Directions links | ✅ OK | All correct |
| Single H1 per page | ⚠️ FIX | All 3 have **two** H1s (nav logo + hero) |
| Meta title / description | ✅ OK | All present |
| Canonical link | ⚠️ MISSING | None of the 3 pages have one |
| Internal cross-links | ✅ OK | All pages link to each other correctly |
| Images alt text | ✅ OK | No `<img>` tags; icon components use `aria-label` |

## Proposed Changes

### All 3 Location Pages

#### Fix 1: Duplicate H1 → single H1

**Line 173** (all 3 files): Change the nav logo from `<h1>` to `<span>`.

```diff
-<h1 class="font-serif text-2xl tracking-widest ...">NIKOS IOANNOU</h1>
+<span class="font-serif text-2xl tracking-widest ...">NIKOS IOANNOU</span>
```

The actual page H1 (e.g., "Jewelry Store in Limassol") remains the sole H1.

---

#### Fix 2: Google Maps iframe → proper embed URLs

Replace fabricated place ID embeds with search-based embeds that reliably resolve:

| Page | Address | New embed URL |
|---|---|---|
| Limassol | Arch. Makarios III Avenue 242, Limassol 3105 | `https://www.google.com/maps?q=Nikos+Ioannou+Jewellers,+Arch.+Makarios+III+Avenue+242,+Limassol+3105,+Cyprus&output=embed` |
| Nicosia Old Town | Onasagorou 79, Nicosia 1011 | `https://www.google.com/maps?q=Nikos+Ioannou+Jewellers,+Onasagorou+79,+Nicosia+1011,+Cyprus&output=embed` |
| Nicosia Makarios | Arch. Makarios III Ave 33, Nicosia 1065 | `https://www.google.com/maps?q=Nikos+Ioannou+Jewellers,+Arch.+Makarios+III+Ave+33,+Galaxias+Shopping+Centre,+Nicosia+1065,+Cyprus&output=embed` |

---

#### Fix 3: Add canonical link

Add to `<head>` after the favicon line:

```html
<link rel="canonical" href="https://nikosioannou.com/{page-slug}">
```

---

#### Fix 4: Enhance JSON-LD schema

Add `description` and `hasMap` properties:

```diff
 "@type": "JewelryStore",
 "name": "Nikos Ioannou Jewellers - Limassol",
+"description": "Luxury jewelry store in Limassol ...",
+"hasMap": "https://www.google.com/maps?q=...",
```

---

### File-by-File Summary

#### [MODIFY] [limassol-jewelry-store.html](file:///C:/Users/mar1/.gemini/antigravity/scratch/niassets/limassol-jewelry-store.html)
- L173: `<h1>` → `<span>` in nav logo
- L18+: Add canonical link
- L443: Replace maps iframe src
- L548-591: Add `description` + `hasMap` to JSON-LD

#### [MODIFY] [nicosia-jewelry-old-town.html](file:///C:/Users/mar1/.gemini/antigravity/scratch/niassets/nicosia-jewelry-old-town.html)
- L173: `<h1>` → `<span>` in nav logo
- L18+: Add canonical link
- L447: Replace maps iframe src
- L552-589: Add `description` + `hasMap` to JSON-LD

#### [MODIFY] [nicosia-jewelry-store.html](file:///C:/Users/mar1/.gemini/antigravity/scratch/niassets/nicosia-jewelry-store.html)
- L173: `<h1>` → `<span>` in nav logo
- L18+: Add canonical link
- L453: Replace maps iframe src
- L558-595: Add `description` + `hasMap` to JSON-LD

## Verification Plan

### Automated (Browser Preview)
1. Start a local server: `npx -y serve ./niassets` in the scratch directory
2. Open each page in browser and verify:
   - Map renders and shows the correct location
   - Only one H1 visible in source
   - Phone links are clickable
   - "Get Directions" opens Google Maps correctly
   - Internal cross-links navigate between pages

### HTML Validation Script
Run a quick grep to confirm:
- Exactly 1 `<h1>` per page
- `<link rel="canonical"` present on each page
- `tel:+357` links present
- `application/ld+json` script block present with `JewelryStore` type
