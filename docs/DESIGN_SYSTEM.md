# Magic UX Design System ✨

## 1. Core Philosophy
- **Glassmorphism**: Heavy use of backdrop-blur, translucent backgrounds, and subtle borders.
- **Premium Typography**: Inter (sans-serif) with tight tracking for headings.
- **Micro-interactions**: Everything interactive must react (scale, glow, color shift).
- **Dark Mode First**: The interface should shine in dark mode with neon accents.

## 2. Color Palette (OKLCH)

We will upgrade the current functional palette to a "Deep Space" theme.

| Token | Previous | New (Magic) | Usage |
|-------|----------|-------------|-------|
| `background` | White/DarkGray | `oklch(0.12 0.02 240)` | Deep blue-black |
| `card` | White/Gray | `oklch(0.15 0.02 240 / 0.7)` | Translucent dark |
| `primary` | Blue/White | `oklch(0.65 0.22 260)` | Neon Purple/Blue |
| `accent` | Gray | `oklch(0.70 0.15 180)` | Cyan Glow |

## 3. Glassmorphism Utilities

```css
.glass-panel {
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.05);
}
```

## 4. Animation Tokens

| Name | value | Usage |
|------|-------|-------|
| `transition-fast` | `all 0.2s cubic-bezier(0.4, 0, 0.2, 1)` | Buttons, Inputs |
| `transition-slow` | `all 0.5s cubic-bezier(0.4, 0, 0.2, 1)` | Modals, Pages |
| `scale-hover` | `scale(1.02)` | Cards |

## 5. UI Polish Plan

1. **Update `app.css`**: Inject new OKLCH palette and glass utilities.
2. **Global Layout**: Add background mesh gradient or subtle pattern.
3. **Sidebar**: Make it glassmorphic (blurred sidebar).
4. **Cards**: Add hover glow effects found in `UsageAnalytics.svelte`.
