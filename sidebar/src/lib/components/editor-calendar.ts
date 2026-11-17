/**
 * The calendar day the two date editors hand the Calendar primitive.
 *
 * The split and the padding are core's; only the shape Bits UI's calendar takes
 * lives here, which is why this is not in core.
 */
import { isoDay, isoDayParts } from 'sg-widgets-core';
import { CalendarDate, type DateValue } from '@internationalized/date';

/** `YYYY-MM-DD` as a calendar day, or undefined when the string is not one (field_types/date). */
export function toCalendarDate(value: string | null | undefined): DateValue | undefined {
	const parts = isoDayParts(value);
	return parts ? new CalendarDate(parts.year, parts.month, parts.day) : undefined;
}

/** The picked day back as `YYYY-MM-DD`, or the empty string when nothing is picked. */
export function fromCalendarDate(value: DateValue | undefined): string {
	if (!value) return '';
	return isoDay({ year: value.year, month: value.month, day: value.day });
}
