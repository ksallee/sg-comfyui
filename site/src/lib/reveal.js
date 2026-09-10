/**
 * Fades an element in once, when it enters the viewport. Under
 * `prefers-reduced-motion: reduce` the element is shown at once.
 *
 * @param {HTMLElement} node
 */
export function reveal(node) {
	if (typeof IntersectionObserver === 'undefined') return;
	if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
		node.classList.add('shown');
		return;
	}

	node.classList.add('reveal');
	const seen = new IntersectionObserver(
		(entries, observer) => {
			for (const entry of entries) {
				if (!entry.isIntersecting) continue;
				entry.target.classList.add('shown');
				observer.unobserve(entry.target);
			}
		},
		{ threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
	);
	seen.observe(node);

	return {
		destroy() {
			seen.disconnect();
		}
	};
}
