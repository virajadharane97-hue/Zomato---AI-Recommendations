---
name: Gourmet Intelligence
colors:
  surface: '#f9f9f9'
  surface-dim: '#dadada'
  surface-bright: '#f9f9f9'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f3f3f3'
  surface-container: '#eeeeee'
  surface-container-high: '#e8e8e8'
  surface-container-highest: '#e2e2e2'
  on-surface: '#1a1c1c'
  on-surface-variant: '#5b403f'
  inverse-surface: '#2f3131'
  inverse-on-surface: '#f1f1f1'
  outline: '#8f6f6e'
  outline-variant: '#e4bebc'
  surface-tint: '#bb162c'
  primary: '#b7122a'
  on-primary: '#ffffff'
  primary-container: '#db313f'
  on-primary-container: '#fffbff'
  inverse-primary: '#ffb3b1'
  secondary: '#835500'
  on-secondary: '#ffffff'
  secondary-container: '#feae2c'
  on-secondary-container: '#6b4500'
  tertiary: '#685a46'
  on-tertiary: '#ffffff'
  tertiary-container: '#81725d'
  on-tertiary-container: '#fffbff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#ffdad8'
  primary-fixed-dim: '#ffb3b1'
  on-primary-fixed: '#410007'
  on-primary-fixed-variant: '#92001c'
  secondary-fixed: '#ffddb4'
  secondary-fixed-dim: '#ffb955'
  on-secondary-fixed: '#291800'
  on-secondary-fixed-variant: '#633f00'
  tertiary-fixed: '#f3e0c6'
  tertiary-fixed-dim: '#d6c4ab'
  on-tertiary-fixed: '#241a0a'
  on-tertiary-fixed-variant: '#514532'
  background: '#f9f9f9'
  on-background: '#1a1c1c'
  surface-variant: '#e2e2e2'
typography:
  h1:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.02em
  h1-mobile:
    fontFamily: Inter
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 34px
    letterSpacing: -0.01em
  h2:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
    letterSpacing: -0.01em
  h3:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '600'
    lineHeight: 24px
  body-lg:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.05em
  caption:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '400'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  base: 4px
  xs: 4px
  sm: 8px
  md: 16px
  lg: 24px
  xl: 32px
  container-max: 1280px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 48px
---

## Brand & Style
The design system is engineered to evoke a "concierge-level" culinary experience. It balances the urgency of hunger with the precision of AI-driven curation. The personality is approachable yet authoritative—mimicking a well-informed food critic who knows your personal palate.

The visual style follows a **Modern Card-Based** approach with a focus on **Tactile Softness**. By utilizing high-contrast primary accents against a muted, high-quality neutral backdrop, the system directs attention toward food photography and AI insights. The aesthetic is clean, generous with whitespace to avoid cognitive overload, and uses subtle depth to categorize information density.

## Colors
The palette is anchored by a vibrant "Appetite Red" and supported by "Action Orange." 

- **Primary (Red):** Used for critical actions, branding, and high-priority highlights.
- **Secondary (Orange):** Reserved for AI-specific accents, ratings, and "warm" recommendations.
- **AI Explanation Tint:** A specific semantic color used as a background for AI-generated reasoning or "Why we picked this" sections to differentiate machine-logic from standard restaurant metadata.
- **Contrast:** Maintain a minimum 4.5:1 contrast ratio for secondary text on all surfaces. In Dark Mode, surfaces use a slight elevation tint (lighter than background) to maintain depth.

## Typography
The system uses **Inter** exclusively to maintain a functional, systematic feel. 

- **Headlines (H1, H2):** Use tighter letter-spacing and bold weights to create a strong visual anchor.
- **Body-LG:** Dedicated to AI-generated summaries and descriptions to ensure high legibility.
- **Labels:** Set in Semi-Bold with slight tracking for use in pill badges, cuisine tags, and rank indicators.
- **Hierarchy:** Use color (Text Secondary) rather than just size to distinguish between primary information (Restaurant Name) and secondary data (Distance, Price Range).

## Layout & Spacing
This design system utilizes a **12-column fluid grid** for desktop and a **4-column fluid grid** for mobile.

- **Sidebar:** On desktop, a 320px fixed-width sticky sidebar is used for filters and "AI Personalization" settings. 
- **Card Rhythm:** Restaurant cards should utilize `md` (16px) internal padding. Vertical stack spacing between cards is `md` (16px) to maintain a dense, browseable list.
- **Whitespace:** Use `lg` (24px) or `xl` (32px) spacing to separate major content sections like "Top Picks" from "Browse All."
- **Touch Targets:** All interactive elements must maintain a minimum 44px height.

## Elevation & Depth
Depth is created through **Ambient Shadows** and tonal layering rather than heavy borders.

- **Level 0 (Background):** Flat, used for the main application canvas.
- **Level 1 (Cards):** 1px subtle border (`border` token) and a soft shadow (0px 2px 8px, 4% opacity).
- **Level 2 (Hover/Active):** Increased shadow spread (0px 8px 20px, 8% opacity) and a slight 2px upward translation to indicate interactivity.
- **Level 3 (Modals/Popovers):** High diffusion shadow (0px 12px 32px, 12% opacity) to isolate the element from the grid.

In Dark Mode, elevation is communicated by lightening the surface hex code of the card relative to the background, rather than relying on shadows which are less visible.

## Shapes
The shape language is consistently **Rounded**, reinforcing the "friendly and appetizing" brand pillar.

- **Standard Cards:** 12px (`rounded-lg`) corner radius.
- **Feature/Hero Cards:** 16px (`rounded-xl`) corner radius.
- **Pills/Badges:** Fully rounded (999px) to contrast against the structured rectangular grid of cards.
- **Images:** Must inherit the corner radius of their parent container. If nested inside a card with 12px radius, the top corners of the image should also be 12px.

## Components
### Buttons
- **Primary:** Solid Red (#E23744), white text, 8px radius.
- **Selection Buttons:** Stacked layout with a light-gray border; when active, they transition to a Red border with a light red tint background.

### Badges & Chips
- **Cuisine Chips:** Pill-shaped, light neutral background, medium-gray text.
- **Rank Badges:** Small circular icons with metallic gradients:
  - Gold (#FFD700) for Rank 1.
  - Silver (#C0C0C0) for Rank 2.
  - Bronze (#CD7F32) for Rank 3.

### Cards
- **Restaurant Card:** Features a large aspect-ratio image (16:9), followed by a title section, a rating row, and an "AI Pick" section at the bottom using the `ai-tint` background.

### Input Fields
- **Search:** Large, 12px radius, leading icon (Search), trailing icon (Filter settings). In Dark Mode, the field background should be slightly darker than the surface.

### AI Reasoning Block
- A specialized component within the card or detail view. It uses the Secondary (Orange) as a left-border accent and the `ai-tint` as the background to signal "Generated Insight."