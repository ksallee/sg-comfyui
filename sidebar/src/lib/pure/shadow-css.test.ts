import { describe, expect, it } from 'vitest';
import { splitForShadow } from './shadow-css';

describe('splitForShadow', () => {
	it('moves each @property rule to the document and keeps the rest for the shadow root', () => {
		const css =
			'@layer base{:host{color:red}}' +
			'@property --tw-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}' +
			'.flex{display:flex}' +
			'@property --tw-ring-offset-width{syntax:"<length>";inherits:false;initial-value:0}';
		const { document, shadow } = splitForShadow(css);
		expect(document).toBe(
			'@property --tw-shadow{syntax:"*";inherits:false;initial-value:0 0 #0000}' +
				'@property --tw-ring-offset-width{syntax:"<length>";inherits:false;initial-value:0}'
		);
		expect(shadow).toBe('@layer base{:host{color:red}}.flex{display:flex}');
	});

	it('leaves css with no @property rule untouched', () => {
		expect(splitForShadow('.a{b:c}')).toEqual({ document: '', shadow: '.a{b:c}' });
	});
});
