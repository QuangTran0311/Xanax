# Static Assets

Put UI assets here.

Suggested layout:

- `favicon.ico` for the browser tab icon
- `images/` for screenshots, logos, and UI illustrations
- `icons/` for any extra SVG or PNG icons

The FastAPI app already mounts `dashboard/static` at `/static`.
Any file placed here can be referenced from the dashboard as:

```text
/static/<path-to-file>
```

