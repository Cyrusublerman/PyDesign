"""Small multi-file project used by the Stage 1 smoke tests."""

from pages.cover import page as cover_page
from pages.principles import page as principles_page

from pydesign import BuildContext, Document


def build(ctx: BuildContext) -> Document:
    return Document(
        id="hello-editorial",
        title="Hello Editorial",
        pages=[cover_page(ctx), principles_page(ctx)],
    )
