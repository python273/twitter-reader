<script>
	import { onMount, onDestroy } from "svelte";
	export let target = globalThis.document?.body;

	let ref;

	onMount(() => {
		if (target) {
			target.appendChild(ref);
		}
	});

	onDestroy(() => {
		setTimeout(() => {
			if (ref?.parentNode) {
				ref.parentNode?.removeChild(ref);
			}
		});
	});
</script>

<div bind:this={ref}>
	<slot />
</div>
