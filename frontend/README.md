# frontend/

React 18 + TypeScript + Vite SPA (built in Phase 5). Target layout:

```
src/
  theme/           # tokens.css + tailwind theme — ONLY source of colors (see docs/design/design-system.md)
  components/ui/   # Token-based design-system components (all states, both themes)
  components/charts/ # SPC chart components (I-MR, X̄-R, histogram+limits, heatmap, stat tiles)
  layouts/         # Sidebar (collapsible), topbar, page shells
  features/        # catalog/ imports/ measurements/ dashboards/ risk/ recommendations/ admin/ profile/
  lib/             # API client, auth, i18n (es/en), preferences
```

Rules: no raw hex in components; every UI PR shows light+dark screenshots; icons only from Lucide; fonts self-hosted.
