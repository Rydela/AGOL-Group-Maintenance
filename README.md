# AGOL Maintenance Scripts

A collection of ready-to-use notebooks for common ArcGIS Online administration tasks. Maintained by the Geospatial Operations Team, World Bank Group.

## Available Scripts

| Script | Description |
|--------|-------------|
| **Bulk Sharing** | Share items to groups and set access levels based on tag rules. Supports dry-run preview, post-run validation, and detailed logging. |

## Quick Start

1. Browse the [`notebooks/`](notebooks/) folder and download the `.ipynb` file you need.
2. Upload it to your ArcGIS Online Notebook environment.
3. Open the notebook, edit the **Configuration** section at the top, and run.

Every notebook includes a `DRY_RUN = True` mode — always preview before applying changes.

## For Contributors

The canonical source for each script lives in [`scripts/`](scripts/) as a plain `.py` file. Notebooks in [`notebooks/`](notebooks/) are auto-generated from these using [Jupytext](https://jupytext.readthedocs.io/).

**Never edit `.ipynb` files directly.** Edit the `.py` source, then regenerate:

```bash
make notebooks
```

See [docs/contributing.md](docs/contributing.md) for the full workflow.

## Repository Structure

```
agol-maintenance/
├── README.md
├── Makefile                 ← converts .py → .ipynb
├── .gitignore
├── scripts/                 ← canonical source (edit these)
│   └── bulk_sharing.py
├── notebooks/               ← auto-generated (do not edit)
│   └── bulk_sharing.ipynb
└── docs/
    └── contributing.md
```

## Requirements

- ArcGIS Online Notebook environment (Python 3.9+)
- Service account or named user with appropriate privileges
- Membership in all target groups (for sharing scripts)

## License

Internal use — World Bank Group.
