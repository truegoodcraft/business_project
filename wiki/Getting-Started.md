# Getting Started

BUS Core is a downloadable, local-first app for inventory, recipes, manufacturing, and cost visibility. It is not a hosted SaaS account, full POS, or full accounting package.

## 1. Choose an Install

- [Windows Install](Windows-Install.md) for the packaged local Windows app.
- [Docker Install](Docker-Install.md) for a container on the same machine.
- [Synology NAS Docker Setup (Beta)](Synology-NAS-Docker-Setup-Beta.md) only if you are testing that community deployment.

Keep the default service on the machine's loopback interface. BUS Core's default setup is not a supported public-server or general multi-user network deployment.

## 2. Choose Demo or Real-Shop Data

On first launch:

- **Demo mode** uses a separate sample database. Use it to explore without mixing sample records into real-shop data.
- **Start Fresh** switches to the production database and initializes a fresh real-shop workspace.

Start Fresh is a reset-like operation. If real-shop data already exists, first open **Settings > Administration > Backup Export**, enter a backup password, export, and confirm the export appears in the list.

## 3. Complete One Small Workflow

Do not enter the full catalog yet. Add one vendor, one material, one product, one recipe, one manufacturing run, and one sale. The [First Shop Workflow](First-Shop-Workflow.md) walks through the sequence.

## 4. Know Where Data Lives

On packaged Windows installs, the production database is under `%LOCALAPPDATA%\BUSCore\app\app.db`; demo data is in `app_demo.db`. Encrypted exports are under `%LOCALAPPDATA%\BUSCore\exports`.

In the default Docker setup, the database is `/data/app.db`. The `/data` directory must be mounted to persistent storage. See [Backup and Restore](Backups-and-Data-Persistence.md) before relying on container recreation or updates.

## 5. Make a Backup

After the first successful workflow, make an encrypted backup export and keep its password somewhere appropriate for your shop. An export you cannot decrypt is not useful.

Next: [First Shop Workflow](First-Shop-Workflow.md).
