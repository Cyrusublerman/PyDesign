# Hello Editorial

This is the executable Stage 1 example. It deliberately uses multiple page modules and stable IDs.

```bash
pydesign check examples/hello_editorial
pydesign render-json examples/hello_editorial --output /tmp/hello-layout.json
pydesign open examples/hello_editorial
```

Text is labelled as a Stage 1 placeholder until the locked ICU/HarfBuzz paragraph engine arrives in Stage 3. It is never presented as production typography.

