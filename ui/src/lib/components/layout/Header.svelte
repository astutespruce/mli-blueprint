<script lang="ts">
	import { resolve } from '$app/paths'

	import FileUpload from '~icons/fa-solid/file-upload'
	import QuestionCircle from '~icons/fa-solid/question-circle'
	import { cn } from '$lib/utils'

	let { hasData = false } = $props()
</script>

<header
	class={cn(
		'flex-none leading-none drop-shadow-sm drop-shadow-black z-10000 bg-primary text-white',
		{
			'hidden md:block': hasData
		}
	)}
>
	<nav
		class="sm:flex flex-auto justify-between items-center gap-3 pl-2 pr-4 py-1"
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
		<div class="hidden flex-none md:flex gap-3 lg:gap-5">
			<a
				href={resolve('/help')}
				target="_blank"
				class="flex gap-1.5 items-center flex-none font-bold text-md bg-transparent hover:bg-black/20 no-underline px-2 py-1.5 border border-white cursor-pointer rounded-sm hover text-white focus:outline-2 focus:outline-accent"
			>
				<QuestionCircle />
				<div class="hidden md:block">How to use this viewer</div>
			</a>

			<a
				href={resolve('/custom_report')}
				class="flex gap-1.5 items-center flex-none font-bold text-md bg-transparent hover:bg-black/20 no-underline px-2 py-1.5 border border-white cursor-pointer rounded-sm text-white focus:outline-2 focus:outline-accent"
			>
				<FileUpload />
				Upload a shapefile
			</a>
		</div>
	</nav>
</header>
