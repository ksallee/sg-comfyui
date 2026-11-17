/**
 * The project the sidebar opens on: the one picked last, else the profile's default, else the
 * first the site lists.
 */
import type { EntityRef } from 'sg-widgets-core';

/** A project as `/sg/projects` lists it. */
export type ProjectItem = { id: number; label: string };

export function startProject(items: ProjectItem[], saved: number, profileDefault: number): EntityRef | null {
	const found =
		items.find((p) => p.id === saved) ?? items.find((p) => p.id === profileDefault) ?? items[0];
	return found ? { type: 'Project', id: found.id, name: found.label } : null;
}
