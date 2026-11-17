/**
 * A glyph per entity type. A stock site has 114 types plus any number of custom
 * ones, so this covers the types a widget meets constantly and falls back to a tag.
 */
import type { Component } from 'svelte';
import Box from '@lucide/svelte/icons/box';
import Clapperboard from '@lucide/svelte/icons/clapperboard';
import FileBox from '@lucide/svelte/icons/file-box';
import Film from '@lucide/svelte/icons/film';
import Folder from '@lucide/svelte/icons/folder';
import ListChecks from '@lucide/svelte/icons/list-checks';
import MessageSquare from '@lucide/svelte/icons/message-square';
import Tag from '@lucide/svelte/icons/tag';
import User from '@lucide/svelte/icons/user';
import Video from '@lucide/svelte/icons/video';

export const ENTITY_GLYPHS: Record<string, Component> = {
	Shot: Clapperboard,
	Asset: Box,
	Sequence: Film,
	Version: Video,
	Task: ListChecks,
	HumanUser: User,
	Project: Folder,
	Note: MessageSquare,
	PublishedFile: FileBox
};

/** The glyph for one type, or the tag every unlisted type takes. */
export function entityGlyph(type: string | null | undefined): Component {
	return ENTITY_GLYPHS[type ?? ''] ?? Tag;
}
