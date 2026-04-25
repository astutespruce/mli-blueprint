<script lang="ts" module>
	import { type VariantProps, tv } from 'tailwind-variants'

	export const alertVariants = tv({
		base: 'relative w-full rounded-lg border px-4 py-3 text-sm ',
		variants: {
			variant: {
				default: '',
				destructive: 'text-destructive bg-destructive/5 border-destructive'
			}
		},
		defaultVariants: {
			variant: 'default'
		}
	})

	export type AlertVariant = VariantProps<typeof alertVariants>['variant']
</script>

<script lang="ts">
	import type { HTMLAttributes } from 'svelte/elements'
	import { cn, type WithElementRef } from '$lib/utils.js'

	let {
		ref = $bindable(null),
		class: className,
		variant = 'default',
		children,
		...restProps
	}: WithElementRef<HTMLAttributes<HTMLDivElement>> & {
		variant?: AlertVariant
	} = $props()
</script>

<div
	bind:this={ref}
	data-slot="alert"
	class={cn(alertVariants({ variant }), className)}
	{...restProps}
	role="alert"
>
	{@render children?.()}
</div>
