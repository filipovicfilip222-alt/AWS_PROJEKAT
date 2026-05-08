# Handoff: PredZnanje Design System

## Overview

This design system establishes the visual and component language for **PredZnanje**, a serverless web application that connects students and professors for consultation scheduling, with integrated AI tutoring. The system defines colors, typography, spacing, component patterns, and interaction models for both student and professor interfaces.

## About the Design Files

The files in this bundle are **design references created in HTML** — high-fidelity previews showing intended look, component states, and interaction patterns. These are **NOT production code to copy directly**. Your task is to:

1. **Extract design tokens** (colors, spacing, type scales) from the reference files
2. **Integrate them into your existing Tailwind + React codebase** using your established patterns
3. **Port component styles and behavior** from the reference HTML into your React component library (leveraging Shadcn/ui, Lucide, Framer Motion as already used)
4. **Maintain the design fidelity** while using your existing build, tooling, and component architecture

## Fidelity

**High-fidelity (hifi)**: All colors, typography, spacing, shadows, and border radii are pixel-perfect specifications. Component states (hover, active, disabled, loading) and animations are defined. The developer should recreate these in React using Tailwind utility classes and existing component patterns, not hardcode the HTML.

## Design System Structure

### Color Palette

**Brand Colors:**
- **Beige Base** (`hsl(39 47% 88%)`): Primary background, warmth anchor
- **Foreground** (`hsl(18 100% 4%)`): Dark ink, nearly black with warmth
- **Primary** (`hsl(236 65% 45%)`): Action, CTA, professor brand (solid blue)
- **Accent** (`hsl(283 84% 53%)`): AI Tutor callout, emphasis (vibrant violet)
- **Border** (`hsl(39 44% 80%)`): Subtle dividers, light mode borders
- **Muted** (`hsl(39 15% 64%)`): Tertiary text, disabled states

**Semantic Colors:**
- Success: `hsl(142 72% 29%)`
- Warning: `hsl(38 92% 50%)`
- Error: `hsl(0 84% 60%)`
- Info: `hsl(236 65% 45%)`

All colors support dark mode via CSS variables. See `colors_and_type.css` for complete token list.

### Typography

**Display Font: Fraunces (Variable)**
- Weights: 500 (regular), 600+ (bold)
- Usage: Headlines (h1–h4), hero text, emphasis
- Features: `cv01` / `cv11` character variants enabled in body; disabled in headings for clarity
- Optical sizing: `opsz` 96–144, `SOFT` 30–50 for warmth and readability at scale

**Body Font: Geist (Variable)**
- Weights: 400 (regular), 500 (medium), 600+ (bold)
- Usage: Body text, labels, UI copy
- Features: `cv01` / `cv11` enabled globally for character swashes
- Size scale: 12px (label) → 16px (body) → 20px (large)

**Type Scale (CSS vars):**
- `--fs-h1`: clamp(2rem, 4vw, 3rem) — 32–48px
- `--fs-h2`: clamp(1.5rem, 3vw, 2.25rem) — 24–36px
- `--fs-h3`: 20px / 1.4
- `--fs-body`: 15px / 1.6
- `--fs-body-sm`: 14px / 1.55
- `--fs-label`: 13px / 1.5 (500 weight)

See `colors_and_type.css` for full specifications.

### Spacing Scale

**8px base unit:**
- 4px, 8px, 12px, 16px, 20px, 24px, 28px, 32px, 40px, 48px, 56px, 64px
- Implemented as `gap`, `margin`, `padding` utilities in Tailwind

### Component Patterns

**Buttons**
- **Variants**: primary (blue bg), secondary (border + transparent), ghost (text only), destructive (red)
- **Sizes**: sm (32px), md (40px), lg (48px)
- **States**: default, hover, active, disabled, loading
- **Icon support**: Left/right icon slots with 6px gap
- **Focus ring**: Blue outline, 2px offset
- See `preview/buttons.html` for full specification

**Cards**
- **Base**: Beige background, subtle border, 8–12px radius
- **States**: default, hover (slight shadow lift), active (border highlight)
- **Content padding**: 16px–20px depending on card type
- See `preview/card-states.html`

**Badges**
- **Variants**: default (gray), primary (blue), success (green), warning (orange), error (red)
- **Sizes**: sm (12px font, tight padding), md (13px, standard)
- **Icon support**: Optional left icon
- See `preview/badges.html`

**AI Tutor Visual Language**
- **Mark**: Violet asterisk (`*`) + "AI Tutor" label, used in nav and message headers
- **Message bubble**: Violet left-border accent, subtle bg, Sparkles icon prefix
- **Confidence badge**: Three tiers (high/medium/low) with color-coded rings
- See `preview/ai-bubbles.html` and `preview/ai-mark.html`

**Forms**
- **Input**: Full-width by default, 40px height, beige bg with subtle border, focus ring
- **Label**: 13px bold, dark text, tight margin-bottom
- **Error state**: Red border + error message (12px, red text)
- **Helper text**: 12px, muted color
- See `preview/forms.html`

### Shadows

- **sm**: `0 1px 2px rgb(0 0 0 / 5%)`
- **md**: `0 4px 6px rgb(0 0 0 / 7%)`
- **lg**: `0 10px 15px rgb(0 0 0 / 10%)`
- **xl**: `0 20px 25px rgb(0 0 0 / 10%)`
- **elevated**: `0 10px 20px rgb(0 0 0 / 12%)`

### Border Radius

- **sm**: 4px
- **md**: 8px
- **lg**: 12px
- **xl**: 16px
- **full**: 9999px (pills, full circles)

## Key Screens & Components

### Student Dashboard
- **Layout**: Two-column (sidebar + main content)
- **Sidebar**: Logo, nav links with icons, AI Tutor featured link in violet
- **Main**: Hero card (dark foreground, violet/blue blob accents), stat cards (icon + metric + label), consultation list
- **Hero card**: 24px padding, Fraunces 36px headline, dark foreground bg, blurred blob overlays
- See `preview/hero.html`, `preview/stat-cards.html`

### Consultation Cards
- **Size**: Variable width, 140px height
- **Content**: Professor avatar, name, subject, time slot, action buttons
- **States**: available (normal), booked (disabled), hover (subtle lift)
- **Interaction**: Click to book / view details

### AI Tutor Panel
- **Position**: Right sidebar or mobile bottom sheet
- **Header**: Violet mark + "AI Tutor" + close button
- **Message area**: Scrollable, message bubbles with alternating alignment
- **Input bar**: Textarea + send button, Sparkles icon
- **Animation**: Fade-in on mount, smooth scroll-to-bottom on new message

### Professor Interface
- **Same color system and components**
- **Role indicator**: Different avatar badge / header emphasis
- **Slot management**: Calendar view, availability toggles, cancellation workflow

## Interactions & Animations

**Transitions:**
- **Default**: 150ms ease-out (button hovers, color shifts)
- **Medium**: 250ms ease-out (card lifts, panel opens)
- **Slow**: 400ms ease-out (page transitions, staggered reveals)

**Hover states:**
- Buttons: 2–4% opacity increase, subtle shadow
- Cards: 2px shadow lift, 1px border color brighten
- Links: Underline appears, color brightens

**Focus ring:**
- 2px solid blue (`hsl(236 65% 45%)`), 2px offset
- Applied to all interactive elements for a11y

**Loading states:**
- Spinner: 2px stroke, 24px size, blue color, 1.5s rotation
- Skeleton: Animated shimmer (left-to-right, 1.5s loop)

**Animations:**
- **Message appear**: Fade-in + 200ms slide-up (Framer Motion)
- **Blob pulse**: Subtle 6s scale loop (optional, low-priority)
- **Button press**: 80ms scale(0.95) feedback

See `frontend/src/styles/motion.ts` for Framer Motion config and easing curves.

## Design Tokens Reference

### CSS Custom Properties (via `colors_and_type.css`)

```css
/* Colors */
--background: 39 47% 88%
--foreground: 18 100% 4%
--primary: 236 65% 45%
--accent: 283 84% 53%
--success: 142 72% 29%
--warning: 38 92% 50%
--error: 0 84% 60%
--border: 39 44% 80%
--muted-foreground: 39 15% 64%

/* Typography */
--font-sans: Geist, system-ui, sans-serif
--font-display: Fraunces, serif

/* Spacing (Tailwind utilities handle these) */
Space scale: 4px, 8px, 12px, 16px, 20px, 24px, 28px, 32px...

/* Shadows */
--shadow-sm: 0 1px 2px rgb(0 0 0 / 5%)
--shadow-md: 0 4px 6px rgb(0 0 0 / 7%)
--shadow-lg: 0 10px 15px rgb(0 0 0 / 10%)
--shadow-elevated: 0 10px 20px rgb(0 0 0 / 12%)
```

## Integration Steps

1. **Copy `colors_and_type.css` values** into your Tailwind `theme` (colors, spacing, fonts)
2. **Update `tailwind.config.ts`** to extend with new color variables and type scales
3. **Port component styles** from preview HTML into React components (leverage existing Shadcn/ui button, badge, card base styles)
4. **Import Fraunces variable font** from Google Fonts (or use local files — see caveats below)
5. **Test dark mode** by toggling Tailwind's dark mode class
6. **Validate responsiveness** at mobile (375px), tablet (768px), desktop (1440px)

## Files in This Bundle

- **colors_and_type.css** — CSS variables and base typography rules (copy into your globals or Tailwind layer)
- **preview/** — High-fidelity HTML reference files for each component and pattern:
  - `colors-brand.html`, `colors-semantic.html` — Color swatches
  - `type-*.html` — Typography scales, families, display usage
  - `buttons.html`, `badges.html`, `cards.html`, `forms.html` — Component variants
  - `ai-bubbles.html`, `ai-mark.html` — AI Tutor specific visuals
  - `hero.html`, `stat-cards.html` — Page patterns
  - `header.html`, `logo.html` — Navigation & branding
- **ui_kits/web/** — React component scaffolds (reference only; refactor into your codebase)
  - `components.jsx` — Button, Badge, Card, Form input primitives
  - `screens.jsx` — Dashboard, consultation list, AI panel examples
  - `styles.css` — Utility classes mirroring Tailwind
- **assets/** — SVG logos (student, professor, AI mark, favicon)
- **README.md** (this file) — Complete specification

## Caveats & Notes

**Font import:**
- Geist is best served from the official npm package (`geist/font`) in `_app.tsx` or layout root
- Fraunces from Google Fonts (`fonts.googleapis.com`) is close but lacks `cv01`/`cv11` variants
- Consider downloading the official Fraunces variable font and self-hosting if character variants are critical

**AI Tutor placeholder content:**
- The preview files use canned responses; the actual `window.claude.complete()` integration happens in your React app
- See `frontend/src/api/aiTutor.ts` for the real API shape

**Dark mode:**
- Design is optimized for light mode (beige base)
- Dark mode CSS variables are defined but untested in these previews
- Test thoroughly in your app before shipping

**Responsive behavior:**
- The design system is mostly fluid (clamp-based type scale)
- On mobile (<640px), button groups may stack; cards may shrink from 240px to 160px
- Sidebar nav collapses to hamburger menu at 640px breakpoint

## Questions for the Team

1. **Color intensity**: Are the primary blue and accent violet saturated enough for your brand, or should they shift warmer/cooler?
2. **Display font**: Is Fraunces the right fit for a Serbian-language academic product? Consider alternatives like Playfair Display or a Cyrillic serif.
3. **AI Tutor prominence**: Is the violet asterisk mark and featured nav item the right visual weight, or should it be louder / quieter?
4. **Logo**: The preview uses procedural SVG lockups. Do you have a final logo to drop in?
5. **Animation preference**: Are the motion curves and durations (150ms, 250ms, 400ms) appropriate for your UX vision?

## Next Steps

1. Review the preview files in the Design System tab to validate colors, type, and component states
2. Create a Tailwind config branch and integrate the color tokens
3. Port component styles into existing Shadcn/ui components
4. Test responsive behavior and dark mode in your app
5. Iterate on interactions and microanimations with your team

---

**Created**: May 8, 2026  
**Design System Version**: 1.0  
**Target Environment**: React 18 + Tailwind CSS + TypeScript  
**Figma**: [Pending — no Figma link yet]
