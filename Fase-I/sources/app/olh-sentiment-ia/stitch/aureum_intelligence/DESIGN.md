# Design System Document: Sentiment Intelligence for Hoteles OLH

## 1. Overview & Creative North Star: "The Nocturnal Intelligence"
This design system is not a mere dashboard; it is a high-end editorial experience designed for the discerning decision-makers of Hoteles OLH. Our Creative North Star is **"The Nocturnal Intelligence."** It envisions a space where data doesn't scream—it glows. 

By prioritizing tonal depth over structural lines, we create an environment that feels like a premium lounge at midnight: sophisticated, focused, and expensive. We break the "SaaS template" look by utilizing intentional asymmetry, where data visualizations are treated as art pieces, and typography follows an editorial hierarchy that guides the eye through narrative rather than just density.

## 2. Colors: Tonal Depth & Sentiment Precision
The palette is rooted in the `surface` (#11131b), providing a void-like canvas that allows our `primary` gold and semantic sentiment colors to radiate with purpose.

### The "No-Line" Rule
**Explicit Instruction:** You are prohibited from using 1px solid borders for sectioning. Structural boundaries must be defined solely through background color shifts or subtle tonal transitions. A `surface-container-low` section sitting on a `surface` background is the standard for separation.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers. Use the container tiers to define importance:
- **`surface_container_lowest` (#0c0e15):** The "sunken" utility layer (e.g., sidebars or footer backgrounds).
- **`surface` (#11131b):** The primary stage for content.
- **`surface_container` (#1d1f27):** Standard card backgrounds.
- **`surface_container_highest` (#32343d):** Elements that require immediate focus or interaction.

### The "Glass & Gradient" Rule
To achieve the "Sentiment Intelligence" feel, use **Glassmorphism** for floating elements (modals, dropdowns, popovers). Use a semi-transparent `surface_variant` with a `backdrop-blur` of 12px to 20px. 
**Signature Texture:** Main CTAs should utilize a subtle linear gradient from `primary` (#f2c35f) to `primary_container` (#d4a847) at a 135° angle to provide a metallic, premium sheen.

## 3. Typography: The Editorial Voice
We contrast the authoritative weight of a serif with the clinical precision of a geometric sans-serif.

*   **Display & Headlines (NotoSerif / Fraunces substitute):** These are our "Editorial Hooks." Use `display-lg` (3.5rem) for high-level sentiment scores. The serif conveys heritage and luxury, reminding the user that Hoteles OLH is a prestige brand.
*   **Titles & Body (Manrope / Outfit substitute):** `title-lg` and `body-md` provide the "Intelligence" layer. These should be set with generous tracking (letter-spacing) in UI labels to maintain a modern, airy feel.
*   **Labels (Inter):** Reserved for technical data points and micro-copy. Use `label-sm` (0.6875rem) in all-caps for "Sentiment Tags" to create a metadata aesthetic.

## 4. Elevation & Depth: Atmospheric Layering
We do not use shadows to mimic light; we use them to mimic **glow**.

*   **The Layering Principle:** Achieve depth by "stacking." A `surface-container-low` card placed on a `surface-container-lowest` background creates a natural lift without high-contrast visual noise.
*   **Ambient Shadows:** When an element must float, use a diffused shadow.
    *   *Values:* `0px 12px 32px`
    *   *Color:* `on_surface` at 4% opacity. This mimics a soft ambient occlusion rather than a "drop shadow."
*   **The "Ghost Border" Fallback:** If a border is required for accessibility, use the `outline_variant` token at **15% opacity**. Never use 100% opaque borders.
*   **Subtle Ambient Glows:** For positive sentiment highlights, use a `tertiary_container` glow (20% opacity) with a 60px blur behind the card to suggest a "radiant" success state.

## 5. Components: Precision & Minimalist Luxury

### Buttons
*   **Primary:** Gradient fill (`primary` to `primary_container`), `on_primary` text. No border. Radius: `md` (0.375rem).
*   **Secondary:** `surface_container_highest` fill with a `primary` "Ghost Border" (20% opacity).
*   **Tertiary:** Ghost button. `on_surface` text with an underline that appears only on hover.

### Sentiment Chips
*   **Positive:** `tertiary_container` background, `on_tertiary_fixed_variant` text.
*   **Critical:** `error_container` background, `on_error_container` text.
*   **Alert:** `primary_container` background, `on_primary_fixed_variant` text.
*   *Note:* Chips must use the `full` (9999px) roundedness for a pill-like, organic feel.

### Input Fields
Avoid the "box" look. Use a `surface_container_low` background with a bottom-only `outline` (2px). On focus, the bottom border transitions to `primary` gold, and a subtle `primary` glow appears behind the field.

### Data Cards & Lists
**Strict Rule:** No divider lines. Separate list items using 16px of vertical white space or a subtle background toggle between `surface_container` and `surface_container_low`. 

### Sentiment "Pulse" (Additional Component)
A custom component for the OLH dashboard: A circular, blurred orb of color (`tertiary` for positive, `error` for critical) that sits behind the main sentiment score, slowly "breathing" (scaling by 5%) to indicate real-time AI processing.

## 6. Do's and Don'ts

### Do
*   **DO** use whitespace as a luxury. Give data room to breathe.
*   **DO** use `inverse_surface` sparingly for high-contrast "Power Moments" (e.g., a total revenue reveal).
*   **DO** ensure that sentiment colors always meet a 4.5:1 contrast ratio against their specific container backgrounds.

### Don't
*   **DON'T** use pure white (#FFFFFF). It shatters the nocturnal atmosphere. Use `on_surface` (#e1e2ed).
*   **DON'T** use 1px dividers to separate sections. Use tonal shifts.
*   **DON'T** use standard "Material" elevation. Our depth is achieved through color nesting and glassmorphism, not heavy drop shadows.