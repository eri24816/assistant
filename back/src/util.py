from bs4 import BeautifulSoup
from bs4.element import PageElement, Tag, NavigableString
from typing import TypeVar


class MyBeautifulSoup(BeautifulSoup):
    def _all_strings(self, strip=False, types=PageElement.default):
        """Yield all strings of certain classes, possibly stripping them.

        :param strip: If True, all strings will be stripped before being
            yielded.

        :param types: A tuple of NavigableString subclasses. Any strings of
            a subclass not found in this list will be ignored. By
            default, the subclasses considered are the ones found in
            self.interesting_string_types. If that's not specified,
            only NavigableString and CData objects will be
            considered. That means no comments, processing
            instructions, etc.

        :yield: A sequence of strings.

        """
        if types is self.default:
            types = self.interesting_string_types

        for descendant in self.descendants:
            if isinstance(descendant, Tag) and descendant.name == "a":
                if not descendant.has_attr('href'):
                    continue
                href = descendant.get('href')
                text = descendant.get_text()
                # clear children
                for child in descendant.children:
                    child.extract()
                # yield markdown link
                yield f"[{text}]({href})"
                continue
            if (types is None and not isinstance(descendant, NavigableString)):
                continue
            descendant_type = type(descendant)
            if isinstance(types, type):
                if descendant_type is not types:
                    # We're not interested in strings of this type.
                    continue
            elif types is not None and descendant_type not in types:
                # We're not interested in strings of this type.
                continue
            if strip:
                descendant = descendant.strip()
                if len(descendant) == 0:
                    continue
            yield descendant


T = TypeVar('T')
def notNone(value: T|None) -> T:
    if value is None:
        raise ValueError("Value is None")
    return value