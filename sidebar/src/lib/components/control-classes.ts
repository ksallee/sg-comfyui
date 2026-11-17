/**
 * The ladder every control in this registry that is not a picker stands on.
 *
 * One height, one inset, one glyph size, so the editors, the search trigger and
 * the filter controls cannot drift from each other or from the React registry.
 * The scale is `docs/design-rules.md` rule 3; a picker's own box, which insets to
 * the chip it holds, is `picker-classes`.
 */

/** The control ladder: the three heights of the design rules. */
export type ControlSize = 'sm' | 'md' | 'lg';

/** The control ladder of `docs/design-rules.md`: 7 / 8 / 9, the shadcn button's own steps. */
export const CONTROL_HEIGHT: Record<ControlSize, string> = {
	sm: 'h-7',
	md: 'h-8',
	lg: 'h-9'
};

/** The leading inset of a control whose value is plain text. */
export const CONTROL_PAD: Record<ControlSize, string> = {
	sm: 'px-2',
	md: 'px-3',
	lg: 'px-3'
};

/** The height and the inset together, which is what an input wears. */
export const CONTROL_BOX: Record<ControlSize, string> = {
	sm: `${CONTROL_HEIGHT.sm} ${CONTROL_PAD.sm}`,
	md: `${CONTROL_HEIGHT.md} ${CONTROL_PAD.md}`,
	lg: `${CONTROL_HEIGHT.lg} ${CONTROL_PAD.lg}`
};

/** A glyph inside a control: `size-4` at sm and md, one step up at lg. */
export const CONTROL_GLYPH: Record<ControlSize, string> = {
	sm: 'size-4',
	md: 'size-4',
	lg: 'size-5'
};

/**
 * The button size a control's step takes. The ladder is the button's own, so each step
 * maps to the button variant of the same height: 28, 32 and 36.
 */
export const CONTROL_BUTTON: Record<ControlSize, 'sm' | 'default' | 'lg'> = {
	sm: 'sm',
	md: 'default',
	lg: 'lg'
};
