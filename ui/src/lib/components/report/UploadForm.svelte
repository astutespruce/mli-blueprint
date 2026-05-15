<script lang="ts">
	import { fromEvent as getFilesFromEvent } from 'file-selector'
	import { superForm, fileProxy, defaults } from 'sveltekit-superforms'
	import { zod4, zod4Client } from 'sveltekit-superforms/adapters'
	import { z } from 'zod'

	import Download from '~icons/fa-solid/download'
	import ExclamationTriangle from '~icons/fa-solid/exclamation-triangle'
	import { CONTACT_URL } from '$lib/env'
	import { cn } from '$lib/utils.js'
	import { Field, Control, Label, Button as SubmitButton } from '$lib/components/ui/form'
	import { Button } from '$lib/components/ui/button'
	import { Input } from '$lib/components/ui/input'
	import { ContactDialog } from '$lib/components/dialog'

	const MAXSIZE_MB = 100
	const MIME_TYPES = new Set([
		'application/zip',
		'application/x-zip-compressed',
		'application/x-compressed',
		'multipart/x-zip'
	])

	const { onSubmit } = $props()
	let isDragValid: boolean | null = $state(null)
	const schema = z.object({
		areaName: z.string().default('').optional(),
		file: z
			.instanceof(File, {
				error: 'Please select a file'
			})
			.refine((f) => f.size < MAXSIZE_MB * 1e6, `File must be less than ${MAXSIZE_MB} MB`)
			.refine(({ type: mimeType }) => MIME_TYPES.has(mimeType), 'File must be a ZIP file')
	})

	const form = superForm(defaults(zod4(schema)), {
		SPA: true,
		validators: zod4Client(schema),
		onUpdate: function ({ form }) {
			const {
				valid,
				data: { areaName = '', file }
			} = form

			if (!valid) {
				return
			}

			onSubmit(areaName, file)
		}
	})

	const { form: formData, enhance, errors, validate } = form
	const fileHandle = fileProxy(formData, 'file')

	const handleDragOver = async (e: DragEvent) => {
		e.preventDefault()
		e.stopPropagation()

		const hasFiles =
			e.dataTransfer &&
			Array.prototype.some.call(
				e.dataTransfer.types,
				(type) => type === 'Files' || type === 'application/x-moz-file'
			)

		if (hasFiles) {
			const files = await getFilesFromEvent(e)
			const [file] = files
			// cannot check file size here, it isn't always defined on file
			isDragValid = files.length === 1 && MIME_TYPES.has(file.type)
		}
	}

	const handleDragOut = (e: DragEvent) => {
		e.preventDefault()
		isDragValid = null
	}

	const handleDrop = async (e: DragEvent) => {
		e.preventDefault()
		isDragValid = null

		const hasFiles =
			e.dataTransfer &&
			Array.prototype.some.call(
				e.dataTransfer.types,
				(type) => type === 'Files' || type === 'application/x-moz-file'
			)

		if (hasFiles) {
			const files = await getFilesFromEvent(e)
			const [file] = files

			if (files.length > 1) {
				alert('Multiple files not allowed')
				return
			}

			fileHandle.set(file as File)
			await validate('file')
		}
	}

	const handleResetFile = async () => {
		form.reset({
			newState: {
				areaName: $formData.areaName
			}
		})
	}

	const handleDropZoneClick = () => {
		const fileInputNode = document.getElementById('file')
		if (fileInputNode) {
			fileInputNode.click()
		}
	}

	const handleDropZoneKeyDown = ({ key }: KeyboardEvent) => {
		const fileInputNode = document.getElementById('file')
		if (fileInputNode && key === 'Enter') {
			fileInputNode.click()
		}
	}

	const isFileValid = $derived($formData.file && !$errors.file)
	const isValid = $derived(isFileValid && !$errors.areaName)
</script>

<div class="container text-lg pt-12 pb-16 leading-snug">
	<div class="grid grid-cols-2 gap-16">
		<div>
			<form enctype="multipart/form-data" use:enhance>
				<Field {form} name="areaName">
					<Control>
						{#snippet children({ props })}
							<Label for="areaName" class="text-2xl font-bold">Area Name (optional):</Label>
							<Input {...props} bind:value={$formData.areaName} class="mt-2" />
						{/snippet}
					</Control>
				</Field>

				<Field {form} name="file" class="mt-12">
					<Control>
						{#snippet children({ props })}
							<Label
								for="file"
								class="block"
								ondragover={handleDragOver}
								ondrop={handleDrop}
								ondragleave={handleDragOut}
							>
								<div class="text-2xl font-bold">Choose Area of Interest:</div>
								<Input
									type="file"
									{...props}
									id="file"
									bind:files={$fileHandle}
									accept={[...MIME_TYPES].join(',')}
									multiple={false}
									class="mt-2 hidden"
								/>
								<div
									class={cn(
										'border-2 border-grey-9/50 rounded-lg bg-grey-1/40 border-dashed p-6 flex flex-col justify-center items-center text-center cursor-pointer mt-2',
										{
											'border-error': isDragValid === false || $errors.file,
											'bg-error/10': isDragValid === false || $errors.file,
											'cursor-not-allowed': isDragValid === false,
											'border-ok': isDragValid === true,
											'bg-ok/10': isDragValid === true,
											hidden: isFileValid
										}
									)}
									onclick={handleDropZoneClick}
									onkeydown={handleDropZoneKeyDown}
									role="button"
									aria-label="Click to browse for files or drop file over this area"
									tabindex={0}
								>
									<div>
										<Download class="size-8" aria-hidden="true" />
									</div>
									<p class="text-2xl font-bold mt-2">Drop your zip file here</p>
									<p class="text-lg text-grey-8 leading-tight mt-4">
										Zip file must contain all associated files for a shapefile (at least .shp, .prj,
										.shx) <br />or file geodatabase (.gdb).
										<br />
										<br />
										Max size: {MAXSIZE_MB} MB.
									</p>
								</div>

								{#if isFileValid}
									<div class="text-lg ml-4">
										Selected: {$formData.file.name}
									</div>
								{/if}
							</Label>

							{#if $errors.file}
								<div class="flex items-center gap-2 text-accent ml-2 mt-4 mb-8">
									<ExclamationTriangle width="1em" height="1em" />
									{$errors.file}
								</div>
							{/if}
						{/snippet}
					</Control>
					<p class="text-sm text-grey-8 mx-4">
						Note: your files must be in a zip file, and can include only one shapefile or Feature
						Class, and should represent a relatively small area. For help analyzing larger areas,
						please <ContactDialog>
							<span class="text-link hover:underline cursor-pointer"> contact us</span>
						</ContactDialog>.
					</p>
				</Field>

				<div class="flex justify-between border-t border-t-grey-2 pt-8 mt-8">
					<div>
						{#if isFileValid}
							<Button onclick={handleResetFile} variant="outline" class="text-xl"
								>Choose a different file</Button
							>
						{/if}
					</div>
					<SubmitButton disabled={!isValid} class="text-xl">Create Report</SubmitButton>
				</div>
			</form>
		</div>
		<div>
			<p>
				Upload a zipped shapefile or ESRI File Geodatabase Feature Class containing your area of
				interest to generate a detailed PDF report of the blueprint, underlying indicators, and
				other contextual information for your area of interest. It includes a map and summary table
				for every indicator present in the area, as well as additional information about
				urbanization and sea-level rise.
				<br />
				<br />
				Don&apos;t have a shapefile? You can create one using
				<a href="https://geojson.io" target="_blank"> geojson.io </a>
				to draw your area of interest, save as a shapefile, then upload here.
				<br />
				<br />
				<ContactDialog>
					<span class="text-link hover:underline cursor-pointer">We are here</span>
				</ContactDialog>
				to help you interpret and apply this information to your particular application!
				<br />
				<br />
				We have made every possible effort to ensure that the information provided in this viewer is accessible
				to people with disabilities. If you cannot fully access the information, please reach out to
				<a href={CONTACT_URL} target="_blank"> Midwest Landscape Initiative staff </a>
				so that we can provide the information in an alternate format.
				<br />
				<br />
				You can help us improve the blueprint and this report by helping us understand your use case:
				we use this information to provide statistics about how the blueprint is being used and to prioritize
				improvements.
			</p>
		</div>
	</div>

	<hr />

	<h2 class="text-2xl">Examples of what is inside</h2>

	<div class="grid grid-cols-2 md:grid-cols-5 mt-2 gap-4 [&_img]:border [&_img]:border-grey-2">
		<enhanced:img src="$images/report/report_sm_1.png" alt="Tool report example screenshot 1" />
		<enhanced:img src="$images/report/report_sm_2.png" alt="Tool report example screenshot 2" />
		<enhanced:img src="$images/report/report_sm_3.png" alt="Tool report example screenshot 3" />
		<enhanced:img src="$images/report/report_sm_4.png" alt="Tool report example screenshot 4" />
		<enhanced:img src="$images/report/report_sm_5.png" alt="Tool report example screenshot 5" />
	</div>
	<p class="mt-2 text-lg">...and much more!</p>
</div>
