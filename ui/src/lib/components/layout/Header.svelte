<script lang="ts">
	import { resolve } from '$app/paths'

	import FileUpload from '~icons/fa-solid/file-upload'
	import InfoCircle from '~icons/fa-solid/info-circle'
	import ViewerIcon from '~icons/fa-solid/map'
	import FeedbackIcon from '~icons/fa-solid/comment-dots'
	import { Button } from '$lib/components/ui/button'
	import { cn } from '$lib/utils'

	let { hasData = false } = $props()
</script>

<header
	class={cn(
		'flex-none leading-none drop-shadow-sm drop-shadow-black z-10000 bg-blue-9 text-white',
		{
			'hidden md:block': hasData
		}
	)}
>
	<nav
		class="sm:flex flex-auto flex-wrap lg:justify-between items-center gap-3 pl-2 pr-4 py-1"
		aria-label="Main navigation"
	>
		<a
			href={resolve('/')}
			class="lg:flex gap-1.5 flex-wrap items-center no-underline text-white hover:text-white focus:outline-2 outline-accent outline-offset-6"
		>
			<div
				class="m-0 font-normal md:font-bold leading-none text-[0.8rem] md:text-[1rem] lg:text-2xl"
			>
				Midwest
			</div>
			<div class="m-0 font-normal md:font-bold text-lg md:text-2xl leading-none">
				Conservation Blueprint Explorer
			</div>
		</a>
		<div class="hidden flex-none md:flex gap-3">
			<Button href={resolve('/help')} target="_blank" variant="header">
				<InfoCircle />
				<div class="hidden md:block">Instructions</div>
			</Button>

			<Button href={resolve('/custom_report')} variant="header">
				<FileUpload />
				Upload a shapefile
			</Button>
			<Button
				href="https://experience.arcgis.com/experience/d05669f0532247bc96fffa8e3820f498/page/Viewer"
				target="_blank"
				variant="header"
			>
				<ViewerIcon />
				Viewer</Button
			>
			<Button
				href="https://experience.arcgis.com/experience/d05669f0532247bc96fffa8e3820f498/page/Feedback"
				target="_blank"
				variant="header"
			>
				<FeedbackIcon />

				Feedback app
			</Button>
		</div>
	</nav>
</header>
