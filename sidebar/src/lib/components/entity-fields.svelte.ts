/**
 * One entity type's fields, read through the context and kept.
 *
 * The schema service caches, so this reaches the network once per type however
 * often the widget redraws (probe 002).
 */
import type { FieldSchema, SgContext } from 'sg-widgets-core';

export interface EntityFields {
	/** The fields by name. Empty until the first read lands. */
	readonly current: Record<string, FieldSchema>;
}

export function entityFields(context: () => SgContext, entityType: () => string): EntityFields {
	let fields = $state<Record<string, FieldSchema>>({});
	$effect(() => {
		let live = true;
		void context()
			.schema.fields(entityType())
			.then((loaded) => {
				if (live) fields = loaded;
			});
		return () => {
			live = false;
		};
	});
	return {
		get current() {
			return fields;
		}
	};
}
