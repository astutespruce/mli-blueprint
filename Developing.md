# Midwest Conservation Blueprint Explorer - Local Development

## Architecture

This uses a data processing pipeline in Python to prepare all spatial data for use in this application.

The user interface is creating using [SvelteJS](https://svelte.dev/) as a static web application.

The API is implemented in Python and provides summary reports for pre-defined summary units and user-defined areas.

## Data analysis & API development

Python dependencies are managed using `uv`. First,
[install uv](https://docs.astral.sh/uv/), then:

```bash
uv venv .venv --python 3.12

uv sync --all-extras --frozen
```

To check for outdated dependencies and upgrade them:

```bash
uv pip list --outdated

# install latest version
uv sync --upgrade --all-extras
```

To update the requirements.txt file used to build these dependencies into the API
Docker container for deployment, run:

TODO: consolidate; these should be exactly the same versions between both

```bash
uv pip compile -U pyproject.toml -o ../secas-docker/docker/api/mli-blueprint-requirements.txt
```

### Other dependencies

On MacOS, install other dependencies:

```bash
brew install gdal pango redis
```

For Macos M1 (Arm64), you may also need to setup symlinks for some of the libraries
to be found:

```bash
sudo ln -s /opt/homebrew/opt/glib/lib/libgobject-2.0.0.dylib /usr/local/lib/gobject-2.0
sudo ln -s /opt/homebrew/opt/pango/lib/libpango-1.0.dylib /usr/local/lib/pango-1.0
sudo ln -s /opt/homebrew/opt/harfbuzz/lib/libharfbuzz.dylib /usr/local/lib/harfbuzz
sudo ln -s /opt/homebrew/opt/fontconfig/lib/libfontconfig.1.dylib /usr/local/lib/fontconfig-1
sudo ln -s /opt/homebrew/opt/pango/lib/libpangoft2-1.0.dylib /usr/local/lib/pangoft2-1.0
```

### Data processing

Source data is shared with the Southeast Blueprint Explorer project. It is
expected that that project is developed locally in `../secas-blueprint` compared
to the root folder of this project.

## User interface development

The user interface is developed using Javascript, executed in NodeJS during a
dedicated build step to build the user interface into static assets, which are
then rendered in the browser.

Install NodeJS using `nvm` using the instructions [here](https://github.com/nvm-sh/nvm).
The version of NodeJS is specified in `ui/.nvmrc`.

Once `nvm` is installed, activate the correct version of NodeJS using:

```bash
cd ui
nvm use
```

Note: this needs to be done each time an interpreter is opened for development.

The user interface is developed using SvelteJS and Typescript. While we don't
strictly require type annotations, we recommend using them where possible, and are
progressively adding type annotations throughout the codebase.

To run the user interface in development mode:

```bash
npm run dev -- --open
```

This will automatically open the development version in your browser.

To run a static build of the user interface:

```bash
npm run build
npm preview -- --open
```

To check for outdated dependencies and upgrade them:

```bash
npm install -g npm-check-updates
ncu -i --cooldown 3
```

Note: this uses a 3 day "cooldown" to prevent upgrading to very recently released
versions; modify this on a selective basis to pull in a newer version that resolves
a vulnerability.

## Other dependencies

Tilesets are created using `tippecanoe` (installed via homebrew) or
[`rastertiler-rs`](https://github.com/brendan-ward/rastertiler-rs) built from
source. See [analysis/prep/tiles/README](./analysis/prep/tiles/README.md) for more information
