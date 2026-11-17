/**
 * The ladders and the chrome every leaf atom in this registry wears.
 *
 * An avatar sits on the thumbnail ladder of `docs/design-rules.md` (6 / 8 / 10). A chip
 * and a badge take that ladder with one step under it (5 / 6 / 8 / 10), so a chip inside
 * the smallest control still has room around it. The cross inside a badge or a chip is
 * one control drawn one way.
 */

/** The leaf ladder: the three sizes an avatar takes. */
export type LeafSize = 'sm' | 'md' | 'lg';

/** The chip ladder: the leaf ladder with a step under it, for a chip in a small control. */
export type ChipSize = 'xs' | LeafSize;

/** A glyph inside an avatar, or a status glyph drawn bare as a row's leading mark. */
export const LEAF_GLYPH: Record<LeafSize, string> = {
	sm: 'size-4',
	md: 'size-4',
	lg: 'size-5'
};

/** The pill a chip or a badge sits in: its height, its type step and medium weight. */
export const CHIP_BOX: Record<ChipSize, string> = {
	xs: 'h-5 text-xs font-medium',
	sm: 'h-6 text-xs font-medium',
	md: 'h-8 text-sm font-medium',
	lg: 'h-10 text-sm font-medium'
};

/** A glyph inside a chip or a badge, a step under the type so the label leads. */
export const CHIP_GLYPH: Record<ChipSize, string> = {
	xs: 'size-3',
	sm: 'size-3.5',
	md: 'size-4',
	lg: 'size-5'
};

/**
 * A chip's inline padding, optically aligned. A bare text edge takes `text`; the edge beside
 * a leading glyph takes `lead`, a step less, since the glyph's own shape already reads as
 * space. The edge beside a cross takes `trail`, the room above the cross's box, so the
 * box sits as far from the right edge as from the top. A glyph with no text takes `icon`.
 */
export const CHIP_PAD: Record<ChipSize, { text: string; lead: string; trail: string; icon: string }> = {
	xs: { text: 'px-1.5', lead: 'pl-1', trail: 'pr-px', icon: 'px-1' },
	sm: { text: 'px-2', lead: 'pl-1.5', trail: 'pr-0.5', icon: 'px-1' },
	md: { text: 'px-2', lead: 'pl-1.5', trail: 'pr-[5px]', icon: 'px-1.5' },
	lg: { text: 'px-2.5', lead: 'pl-2', trail: 'pr-2', icon: 'px-2' }
};

/**
 * The cross inside a chip or a badge. It grows a step with the chip; its box is the icon and
 * `REMOVE_CONTROL`'s 2px padding.
 */
export const CHIP_CROSS: Record<ChipSize, string> = {
	xs: 'size-3',
	sm: 'size-3.5',
	md: 'size-4',
	lg: 'size-4.5'
};

/**
 * The space inside a chip: `glyph` between a leading glyph and the label, `cross` before the
 * cross, a step less, since the cross's own padding already reads as space.
 */
export const CHIP_SPACING: Record<ChipSize, { glyph: string; cross: string }> = {
	xs: { glyph: 'gap-1', cross: 'gap-0.5' },
	sm: { glyph: 'gap-1', cross: 'gap-0.5' },
	md: { glyph: 'gap-1.5', cross: 'gap-1' },
	lg: { glyph: 'gap-1.5', cross: 'gap-1' }
};

/**
 * The cross inside a badge or a chip. It hovers with a wash of its own
 * foreground rather than the destructive tint, so the two read the same
 * (`docs/design-rules.md` rule 5).
 *
 * A coarse pointer gets a 44px box centred on the cross, drawn as a pseudo-element so
 * the chip keeps its own size and nothing around it moves.
 */
export const REMOVE_CONTROL =
	"hover:bg-current/8 focus-visible:ring-ring focus-visible:ring-offset-background shrink-0 rounded-sm p-0.5 opacity-70 outline-none transition-colors duration-150 hover:opacity-100 focus-visible:ring-2 focus-visible:ring-offset-2 motion-safe:active:scale-[0.98] pointer-coarse:relative pointer-coarse:before:absolute pointer-coarse:before:top-1/2 pointer-coarse:before:left-1/2 pointer-coarse:before:size-11 pointer-coarse:before:-translate-x-1/2 pointer-coarse:before:-translate-y-1/2 pointer-coarse:before:content-['']";
