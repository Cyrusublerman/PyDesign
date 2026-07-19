# Hello Editorial

This is tracked executable documentation for the Stage 1 example. It deliberately uses multiple
page modules and stable IDs. Do not use this repository directory for personal work: the desktop
application offers to create an editable external copy, or copy it explicitly with:

```bash
pydesign duplicate examples/hello_editorial "/external/path/Hello Editorial"
```

```bash
pydesign check examples/hello_editorial
pydesign render-json examples/hello_editorial --output /tmp/hello-layout.json
pydesign open examples/hello_editorial
```

Text is labelled as a Stage 1 placeholder until the locked ICU/HarfBuzz paragraph engine arrives in Stage 3. It is never presented as production typography.
