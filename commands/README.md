# Creating local reports for large areas

The online version of the tool limits the size and complexity of the input file
to prevent overwhelming the server.

It is possible to bypass these limits by creating reports on your local computer.
You need to have everything installed for development on this repository (see
[Developing.md](../Developing.md')).

The commands are installed automatically by running


```bash
uv sync --all-extras
```


From the root of the repository, run

```bash
create-report --help
```

This will list the available commands.


## PDF reports

Run

```bash
create-report pdf --help
```

For instructions on required and optional parameters.


## XLSX reports

Run

```bash
create-report xlsx --help
```

For instructions on required and optional parameters.



