# DECP --- Server Installation & Docker Deployment Guide

**Department Engineering Cloud (DECP)**\
A practical guide for anyone who wants to convert a fresh PC into the
DECP private cloud server using Docker.

------------------------------------------------------------------------

## 1. What This Guide Does

This guide takes a **fresh Ubuntu Server PC** and turns it into a DECP
server that can run:

-   React frontend
-   FastAPI backend
-   PostgreSQL database
-   NGINX reverse proxy
-   Docker containers
-   Persistent student/project file storage
-   Authentication and role-based access
-   Department project hosting

The recommended deployment model is:

``` text
                    Department LAN
                         |
                     Students
                         |
                    Web Browser
                         |
                         v
                +----------------+
                |     NGINX      |
                | Reverse Proxy  |
                +-------+--------+
                        |
              +---------+---------+
              |                   |
              v                   v
        React Frontend       FastAPI Backend
                                  |
                                  v
                           PostgreSQL DB
                                  |
              +-------------------+------------------+
              |                                      |
              v                                      v
       User/File Metadata                    Docker Storage
                                              /cloud-data
                                                   |
                                                   v
                                           Department HDD
```

------------------------------------------------------------------------

# 2. Recommended Server Hardware

For the current department setup, the recommended configuration is:

  Component      Recommended
  -------------- ----------------------------------------
  CPU            Intel Core i5 12th Gen or better
  RAM            32 GB recommended; 16 GB minimum
  OS SSD         512 GB SSD or larger
  Data Storage   Additional HDDs
  Network        Gigabit Ethernet
  GPU            Not required for the current DECP core
  UPS            Strongly recommended

### Storage recommendation

Use the SSD for:

-   Ubuntu
-   Docker
-   PostgreSQL
-   Application files

Use HDD storage for:

-   Student files
-   Project datasets
-   Backups
-   Archived projects

> **Important:** Never format an existing department HDD until you have
> confirmed that it contains no required data and that a backup exists.

------------------------------------------------------------------------

# 3. Operating System

Use:

**Ubuntu Server 24.04 LTS**

During installation:

-   Install Ubuntu Server
-   Give the server a meaningful hostname, for example:

``` text
decp-server
```

-   Create an administrator account
-   Enable OpenSSH Server if remote administration is required
-   Use the SSD for the operating system

After installation, log in.

------------------------------------------------------------------------

# 4. Update the Server

Run:

``` bash
sudo apt update
sudo apt upgrade -y
```

Reboot if required:

``` bash
sudo reboot
```

Reconnect after the reboot.

------------------------------------------------------------------------

# 5. Install Basic Tools

Install Git and useful utilities:

``` bash
sudo apt install -y git curl ca-certificates
```

Check:

``` bash
git --version
curl --version
```

------------------------------------------------------------------------

# 6. Install Docker

Install Docker using Docker's official repository/instructions.

After Docker is installed, verify:

``` bash
docker --version
```

Also verify Docker Compose:

``` bash
docker compose version
```

The DECP project uses the modern Docker Compose command:

``` bash
docker compose
```

not the older:

``` bash
docker-compose
```

------------------------------------------------------------------------

# 7. Allow the Current User to Run Docker

Add your user to the Docker group:

``` bash
sudo usermod -aG docker $USER
```

Then log out and log back in.

Verify:

``` bash
docker run hello-world
```

If this works without `sudo`, Docker is ready.

------------------------------------------------------------------------

# 8. Configure the Server Network

Find the server's IP:

``` bash
ip addr
```

or:

``` bash
hostname -I
```

Example:

``` text
192.168.1.50
```

Students on the same department LAN can then access:

``` text
http://192.168.1.50
```

### Recommended

Give the server a **static IP** or configure a DHCP reservation on the
department router/network.

Example:

``` text
Server hostname: decp-server
Server IP:       192.168.1.50
```

A stable IP is important because students and administrators need a
consistent address.

------------------------------------------------------------------------

# 9. Clone the DECP Project

Go to a suitable directory:

``` bash
cd ~
```

Clone the GitHub repository:

``` bash
git clone <YOUR-GITHUB-REPOSITORY>
```

Enter the project:

``` bash
cd Department-Engineering-Cloud
```

> Replace `<YOUR-GITHUB-REPOSITORY>` with the actual GitHub repository
> URL.

Check:

``` bash
ls
```

You should see files/directories similar to:

``` text
backend/
frontend/
nginx/
docker-compose.yml
.env.example
.gitignore
README.md
docs/
```

------------------------------------------------------------------------

# 10. Create the Environment File

Copy the example environment file:

``` bash
cp .env.example .env
```

Open it:

``` bash
nano .env
```

Configure the values required by the project.

At minimum, pay attention to:

-   Database configuration
-   JWT secret
-   Storage path
-   Any application-specific environment variables

### Security rule

Do **not** commit `.env` to GitHub.

The repository should contain:

``` text
.env.example
```

but the real:

``` text
.env
```

must remain private.

------------------------------------------------------------------------

# 11. Configure Persistent Storage

DECP stores the actual uploaded files on the server filesystem.

PostgreSQL stores metadata such as:

-   User information
-   Folder information
-   File names
-   File metadata
-   Ownership information

The actual file bytes are stored in the filesystem.

Current Docker storage configuration uses:

``` text
STORAGE_HOST_PATH -> /cloud-data
```

For development, this can be a project-local directory.

For the real department server, use a dedicated data disk/HDD.

------------------------------------------------------------------------

# 12. Prepare the Department HDD

First identify available disks:

``` bash
lsblk
```

Example:

``` text
NAME   SIZE TYPE MOUNTPOINT
sda    512G disk
├─sda1 ...
sdb      4T disk
```

**Do not run formatting commands until you are certain which disk is
safe to use.**

If a new/empty disk is approved for DECP storage, it can be partitioned
and formatted according to the department's storage policy.

Then create a mount point:

``` bash
sudo mkdir -p /cloud-data
```

Mount the approved data disk there.

Verify:

``` bash
df -h
```

You should see the storage disk mounted at:

``` text
/cloud-data
```

### Persistent mounting

Configure the disk in `/etc/fstab` using its UUID so it is automatically
mounted after a reboot.

Find the UUID:

``` bash
sudo blkid
```

Before editing `/etc/fstab`, make sure the UUID and filesystem type are
correct.

Test the configuration:

``` bash
sudo mount -a
```

Then verify:

``` bash
df -h
```

------------------------------------------------------------------------

# 13. Configure DECP to Use the Data Disk

Edit:

``` bash
nano .env
```

Set the storage host path according to the project's Docker Compose
configuration.

For example:

``` env
STORAGE_HOST_PATH=/cloud-data
```

The project should map:

``` text
Host:
/cloud-data

        ↓ Docker bind mount

Container:
/cloud-data
```

This means uploaded files survive container recreation.

------------------------------------------------------------------------

# 14. Build the Docker Stack

From the project root:

``` bash
docker compose build
```

Then start the services:

``` bash
docker compose up -d
```

Or build and start in one command:

``` bash
docker compose up -d --build
```

Check running containers:

``` bash
docker compose ps
```

You should see the DECP services running.

------------------------------------------------------------------------

# 15. Run Database Migrations

After the containers are running:

``` bash
docker compose exec backend alembic upgrade head
```

This creates/updates the PostgreSQL database schema.

Check the backend:

``` bash
curl http://localhost:8080/api/health
```

The exact response depends on the current application implementation,
but it should indicate that the API is healthy.

------------------------------------------------------------------------

# 16. Test the Website

From the server itself:

``` bash
curl http://localhost:8080
```

From another PC connected to the same department network, open:

``` text
http://SERVER_IP:8080
```

For example:

``` text
http://192.168.1.50:8080
```

If NGINX is configured to listen on port 80 in the production setup, the
final URL may instead be:

``` text
http://192.168.1.50
```

Use the port defined by the current `docker-compose.yml` and NGINX
configuration.

------------------------------------------------------------------------

# 17. Verify Authentication

Open the DECP web interface.

Test:

1.  Student registration
2.  Login
3.  Dashboard
4.  Logout
5.  Invalid login
6.  Protected API access
7.  Role restrictions

A public registration must not allow a user to register themselves as:

``` text
admin
```

or:

``` text
faculty
```

------------------------------------------------------------------------

# 18. Verify Cloud Storage

After logging in:

1.  Open **My Files**
2.  Create a folder
3.  Upload a file
4.  Download the file
5.  Rename the file
6.  Delete the file
7.  Create a nested folder
8.  Upload another file
9.  Check storage usage

Verify the physical storage:

``` bash
sudo ls -lah /cloud-data
```

------------------------------------------------------------------------

# 19. Verify Docker Persistence

List containers:

``` bash
docker compose ps
```

Restart the stack:

``` bash
docker compose restart
```

Then verify:

-   Users still exist
-   Uploaded files still exist
-   Database records still exist

For a stronger test:

``` bash
docker compose down
docker compose up -d
```

Then verify the same data again.

**Never use `docker compose down -v` casually in production**, because
removing volumes can delete persistent database data.

------------------------------------------------------------------------

# 20. Useful Docker Commands

### See running containers

``` bash
docker compose ps
```

### View all logs

``` bash
docker compose logs
```

### Follow logs

``` bash
docker compose logs -f
```

### Backend logs

``` bash
docker compose logs -f backend
```

### Frontend logs

``` bash
docker compose logs -f frontend
```

### NGINX logs

``` bash
docker compose logs -f nginx
```

### PostgreSQL logs

``` bash
docker compose logs -f postgres
```

### Restart everything

``` bash
docker compose restart
```

### Stop everything

``` bash
docker compose down
```

### Start again

``` bash
docker compose up -d
```

### Rebuild after code changes

``` bash
docker compose up -d --build
```

------------------------------------------------------------------------

# 21. Updating DECP From GitHub

When a new version is pushed to GitHub:

``` bash
cd ~/Department-Engineering-Cloud
```

Pull the latest code:

``` bash
git pull
```

Then rebuild/restart:

``` bash
docker compose up -d --build
```

Run migrations if the update contains database changes:

``` bash
docker compose exec backend alembic upgrade head
```

Check:

``` bash
docker compose ps
```

Then test the application.

------------------------------------------------------------------------

# 22. Recommended Update Workflow

Use this sequence:

``` text
GitHub
   |
   v
git pull
   |
   v
docker compose up -d --build
   |
   v
Database migration
   |
   v
Health check
   |
   v
Manual UI test
```

Never blindly update a production server without checking the
application and database changes.

------------------------------------------------------------------------

# 23. Firewall

For a LAN-only deployment, restrict access to the required ports.

Check firewall status:

``` bash
sudo ufw status
```

If UFW is enabled, allow SSH:

``` bash
sudo ufw allow ssh
```

Allow the HTTP port used by DECP, for example:

``` bash
sudo ufw allow 80/tcp
```

If the application is intentionally exposed on port 8080:

``` bash
sudo ufw allow 8080/tcp
```

Only expose ports that are actually required.

------------------------------------------------------------------------

# 24. SSH Administration

If OpenSSH is enabled, administrators can manage the server remotely:

``` bash
ssh username@SERVER_IP
```

Example:

``` bash
ssh ved@192.168.1.50
```

Use SSH keys rather than passwords where practical.

Do not share administrator credentials with students.

------------------------------------------------------------------------

# 25. Production Storage Layout

A recommended layout is:

``` text
SSD
├── Ubuntu Server
├── Docker
├── PostgreSQL
└── DECP application

HDD
└── /cloud-data
    ├── users/
    ├── projects/
    ├── backups/
    └── archives/
```

The exact directory structure is controlled by the application and
should not be changed manually unless the application configuration is
updated accordingly.

------------------------------------------------------------------------

# 26. Backups

A cloud server is not safe merely because the data is stored on a
server.

At minimum, plan backups for:

### PostgreSQL

Back up the database regularly.

### Student files

Back up:

``` text
/cloud-data
```

### Configuration

Keep a secure copy of:

-   `.env` secrets
-   Docker Compose configuration
-   NGINX configuration
-   Important deployment documentation

Do not put secrets into public GitHub repositories.

------------------------------------------------------------------------

# 27. Important Disaster-Recovery Rule

If the server's SSD fails, the application can be rebuilt from GitHub,
but persistent data must come from backups.

Think of the system as:

``` text
GitHub
   = application source

PostgreSQL
   = application metadata

/cloud-data
   = student/project files

Backup
   = recovery mechanism
```

All four are important.

------------------------------------------------------------------------

# 28. Server Monitoring

Useful commands:

### CPU/RAM

``` bash
htop
```

### Disk usage

``` bash
df -h
```

### Directory size

``` bash
du -sh /cloud-data
```

### Disk information

``` bash
lsblk
```

### Docker resource usage

``` bash
docker stats
```

### Docker disk usage

``` bash
docker system df
```

------------------------------------------------------------------------

# 29. Do Not Run These Commands Carelessly

Be especially careful with:

``` bash
docker compose down -v
```

This can remove Docker volumes.

Also be careful with:

``` bash
docker system prune
```

and:

``` bash
sudo rm -rf
```

Never format a disk unless you have verified that it is the correct disk
and its data is not required.

------------------------------------------------------------------------

# 30. Security Checklist

Before allowing real students to use the server:

-   [ ] Ubuntu is updated
-   [ ] Docker is updated
-   [ ] Strong database password configured
-   [ ] Strong JWT secret configured
-   [ ] `.env` is not committed
-   [ ] Firewall configured
-   [ ] SSH access secured
-   [ ] Admin credentials protected
-   [ ] Student file isolation tested
-   [ ] Storage quotas tested
-   [ ] Database backups configured
-   [ ] File backups configured
-   [ ] Server has UPS protection
-   [ ] Server has stable network connectivity
-   [ ] Existing department data was not overwritten
-   [ ] Recovery procedure has been tested

------------------------------------------------------------------------

# 31. First-Time Deployment Checklist

Use this when setting up a completely fresh PC:

``` text
[ ] Install Ubuntu Server 24.04 LTS
[ ] Set hostname
[ ] Create administrator account
[ ] Install/enable SSH
[ ] Update Ubuntu
[ ] Install Git
[ ] Install Docker
[ ] Verify Docker Compose
[ ] Configure static/reserved LAN IP
[ ] Identify approved data HDD
[ ] Mount data HDD at /cloud-data
[ ] Verify disk persistence
[ ] Clone DECP repository
[ ] Create .env
[ ] Configure secrets
[ ] Configure storage path
[ ] Build Docker images
[ ] Start Docker Compose
[ ] Run Alembic migrations
[ ] Check container health
[ ] Test NGINX
[ ] Test frontend
[ ] Test registration/login
[ ] Test file upload/download
[ ] Test file persistence
[ ] Configure firewall
[ ] Configure backups
[ ] Perform disaster-recovery test
```

------------------------------------------------------------------------

# 32. Day-to-Day Administrator Workflow

### Check server

``` bash
ssh username@SERVER_IP
```

### Check containers

``` bash
cd ~/Department-Engineering-Cloud
docker compose ps
```

### Check resources

``` bash
docker stats
```

### Check storage

``` bash
df -h
```

### Check application logs

``` bash
docker compose logs --tail=100
```

### Update application

``` bash
git pull
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

------------------------------------------------------------------------

# 33. Troubleshooting

## Docker command not found

Check:

``` bash
docker --version
```

If missing, Docker is not installed correctly.

------------------------------------------------------------------------

## Permission denied when running Docker

Check:

``` bash
groups
```

Make sure your user belongs to the Docker group:

``` bash
sudo usermod -aG docker $USER
```

Log out and log back in.

------------------------------------------------------------------------

## Containers are not running

Run:

``` bash
docker compose ps
```

Then:

``` bash
docker compose logs
```

Look for the service reporting an error.

------------------------------------------------------------------------

## Backend is unhealthy

Check:

``` bash
docker compose logs backend
```

Also verify:

``` bash
docker compose ps
```

Check the database:

``` bash
docker compose logs postgres
```

------------------------------------------------------------------------

## Database migration fails

Check the backend logs:

``` bash
docker compose logs backend
```

Then verify the database service is running:

``` bash
docker compose ps
```

Do not delete the database volume just to make a migration error
disappear.

------------------------------------------------------------------------

## Uploaded files disappear

Check the storage configuration.

Verify the host directory:

``` bash
df -h /cloud-data
```

Check:

``` bash
ls -lah /cloud-data
```

Inspect the Compose volume mapping:

``` bash
docker compose config
```

Make sure the host storage is mapped to the expected container path.

------------------------------------------------------------------------

## Website works on server but not another PC

Check:

``` bash
hostname -I
```

Then from another PC:

``` text
http://SERVER_IP
```

Check the firewall:

``` bash
sudo ufw status
```

Check NGINX:

``` bash
docker compose logs nginx
```

Also verify that both machines are actually connected to the same
reachable network.

------------------------------------------------------------------------

# 34. Development vs Production

DECP should be developed on a developer PC and deployed to the
department server.

### Development

``` text
Developer PC
    |
Docker Compose
    |
React + FastAPI + PostgreSQL + NGINX
```

### Production

``` text
Department Server
    |
Ubuntu Server
    |
Docker Compose
    |
React + FastAPI + PostgreSQL + NGINX
    |
Department LAN
```

This means developers do not need to keep the department server
available during development.

------------------------------------------------------------------------

# 35. Important Architecture Principle

Do not think:

> "I installed Docker, so I created a cloud."

Instead:

``` text
Physical Server
      +
Linux
      +
Networking
      +
Docker
      +
Persistent Storage
      +
Database
      +
Authentication
      +
Web Application
      +
Resource Management
      +
Automation
      =
Private Department Cloud
```

Docker provides the containerization layer. The complete cloud
experience comes from the entire infrastructure and software platform
working together.

------------------------------------------------------------------------

# 36. Current DECP Core

The current implementation provides the foundation for:

-   User authentication
-   Role-based access
-   PostgreSQL-backed metadata
-   Personal cloud storage
-   Folder management
-   File upload/download/delete/rename
-   Storage usage/quota handling
-   Dockerized deployment
-   NGINX reverse proxy
-   Persistent storage

Future modules can build on this foundation:

``` text
DECP
 |
 +-- Authentication
 |
 +-- Personal Storage
 |
 +-- Project Repository
 |
 +-- Website Hosting
 |
 +-- Admin Dashboard
 |
 +-- Server Monitoring
 |
 +-- Automated Deployment
 |
 +-- Backups
 |
 +-- Research Data Repository
 |
 +-- Resource Management
 |
 +-- Future AI/Automation Layer
```

------------------------------------------------------------------------

# 37. Fresh Server Quick Start

For an experienced administrator, the high-level process is:

``` bash
# 1. Update system
sudo apt update && sudo apt upgrade -y

# 2. Install basics
sudo apt install -y git curl ca-certificates

# 3. Install Docker
# Follow Docker's official installation instructions.

# 4. Verify
docker --version
docker compose version

# 5. Clone
git clone <YOUR-GITHUB-REPOSITORY>
cd Department-Engineering-Cloud

# 6. Configure environment
cp .env.example .env
nano .env

# 7. Confirm storage disk is mounted
df -h

# 8. Start DECP
docker compose up -d --build

# 9. Apply database migrations
docker compose exec backend alembic upgrade head

# 10. Check services
docker compose ps

# 11. Check logs if required
docker compose logs --tail=100
```

Then open the server's LAN address from a browser.

------------------------------------------------------------------------

# 38. Production Principle

**Do not expose DECP to the public internet during the initial
deployment.**

Start with:

``` text
Students
   |
Department LAN
   |
DECP Server
```

After the system is stable and security has been reviewed, external
access can be considered with appropriate:

-   HTTPS/TLS
-   DNS
-   Firewall rules
-   Authentication hardening
-   Rate limiting
-   Monitoring
-   Backup/recovery
-   Security testing

------------------------------------------------------------------------

# 39. Final Architecture

The intended production architecture is:

``` text
                    ┌──────────────────────┐
                    │  Department Users    │
                    │ Students / Faculty   │
                    └──────────┬───────────┘
                               │
                               │ LAN
                               ▼
                    ┌──────────────────────┐
                    │        NGINX         │
                    │   Reverse Proxy      │
                    └──────────┬───────────┘
                               │
                ┌──────────────┴──────────────┐
                │                             │
                ▼                             ▼
       ┌─────────────────┐          ┌─────────────────┐
       │ React Frontend  │          │ FastAPI Backend │
       └─────────────────┘          └────────┬────────┘
                                             │
                              ┌──────────────┴──────────────┐
                              │                             │
                              ▼                             ▼
                     ┌─────────────────┐          ┌─────────────────┐
                     │   PostgreSQL    │          │ Linux Storage   │
                     │    Metadata     │          │  /cloud-data    │
                     └─────────────────┘          └────────┬────────┘
                                                           │
                                                           ▼
                                                     Department HDD
```

------------------------------------------------------------------------

## 40. Deployment Philosophy

DECP is designed so that the **same Dockerized application can move from
a developer PC to a department server without rebuilding the entire
software stack manually**.

The target workflow is:

``` text
Develop
   ↓
Test locally
   ↓
Push code to GitHub
   ↓
Fresh Ubuntu Server
   ↓
Clone repository
   ↓
Configure .env
   ↓
Mount persistent storage
   ↓
docker compose up -d --build
   ↓
Run migrations
   ↓
Test
   ↓
Department Cloud Online
```

This is the core deployment model for DECP.
