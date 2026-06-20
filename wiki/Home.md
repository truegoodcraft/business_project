> Status: User Guide

# BUS Core Wiki

BUS Core is local-first, open-source shop infrastructure for small makers, workshops, and owner-operators. It tracks inventory, recipes, manufacturing, sales-related stock movement, and cost visibility without requiring a hosted account, forced cloud service, or telemetry.

BUS Core v1.3.2 is the community polish release. Core is now feature-frozen and stability-focused: it remains maintained, while future Core work concentrates on bug fixes, data safety, backup and restore, security and trust, release hygiene, tester blockers, documentation, and small UX clarity. Major new workflow discovery belongs to BUS Pro, not Core.

## Start Here

1. [Getting Started](Getting-Started.md) - choose an install, understand demo versus real-shop data, and prepare a backup.
2. [First Shop Workflow](First-Shop-Workflow.md) - complete one material-to-product workflow before entering a large catalog.
3. [Inventory Guide](Inventory-Guide.md) - understand items, units, batches, FIFO, vendors, and stock movement.
4. [Backup and Restore](Backups-and-Data-Persistence.md) - protect the local data you are responsible for.
5. [Trust, Security, and Local-First](Trust-Security-and-Local-First.md) - understand what stays local and where the deployment boundary is.

## Guides

- [Windows Install](Windows-Install.md)
- [Docker Install](Docker-Install.md)
- [Synology NAS Docker Setup (Beta)](Synology-NAS-Docker-Setup-Beta.md)
- [Recipes Guide](Recipes-Guide.md)
- [Manufacturing Guide](Manufacturing-Guide.md)
- [Finance Guide](Finance-Guide.md)
- [Updates and Releases](Updates-and-Releases.md)
- [Troubleshooting and FAQ](FAQ.md)
- [What BUS Core Does Not Include](Product-Boundaries.md)

## Help and Testing

- [Beta Testing Guide](Beta-Testing-Guide.md)
- [Bug Reports](Bug-Reports.md)
- [Feature Requests](Feature-Requests.md)

This wiki is the operator guide. Engineering authority remains in the repository documents, including `SOT.md`, `API_CONTRACT.md`, and `/docs`.

## How This Wiki Publishes

Edit `/wiki/*.md` in the main repository. On pushes to `main`, GitHub Actions publishes this folder to the GitHub Wiki. The GitHub Wiki must be initialized once with a Home page in the GitHub UI before automated publishing can work reliably.
