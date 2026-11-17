/**
 * The sidebar's stylesheet, split between the document and the shadow root.
 *
 * A browser ignores an `@property` rule inside a shadow root. Tailwind registers its `--tw-*`
 * properties with `@property`, so those rules go in the document and the rest in the shadow root.
 * An `@property` body has no nested braces.
 */
const PROPERTY = /@property\s+--[\w-]+\s*\{[^}]*\}/g;

export function splitForShadow(css: string): { document: string; shadow: string } {
	return {
		document: (css.match(PROPERTY) ?? []).join(''),
		shadow: css.replace(PROPERTY, '')
	};
}
