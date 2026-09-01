# Docker Hub Setup Guide

This guide explains how to set up automatic Docker image builds and publishing to Docker Hub via GitHub Actions.

## Prerequisites

1. **Docker Hub Account**: Create one at https://hub.docker.com if you don't have one
2. **GitHub Repository**: You already have this at https://github.com/yossi-neeman/Zoom2Youtube

## Setup Steps

### 1. Create Docker Hub Access Token

1. Go to https://hub.docker.com/settings/security
2. Click **New Access Token**
3. Name it: `github-actions-zoom2youtube`
4. Permissions: **Read, Write, Delete**
5. Click **Generate**
6. **Copy the token immediately** (you won't see it again)

### 2. Add GitHub Secrets

1. Go to your GitHub repository: https://github.com/yossi-neeman/Zoom2Youtube
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add two secrets:

   **Secret 1:**
   - Name: `DOCKER_USERNAME`
   - Value: `neeman2019` (your Docker Hub username)

   **Secret 2:**
   - Name: `DOCKER_PASSWORD`
   - Value: (paste the access token from step 1)

### 3. Push the Workflow File

The workflow file `.github/workflows/docker-publish.yml` is already in your repository. Just commit and push:

```bash
cd /Users/yossin/workspace/Zoom2Youtube
git add .github/workflows/docker-publish.yml DOCKER_HUB_SETUP.md
git commit -m "Add GitHub Actions workflow for Docker Hub publishing"
git push origin main
```

## How It Works

The GitHub Action will automatically:

1. **Trigger on:**
   - Every push to `main` branch
   - Every tag push (e.g., `v1.0.0`)
   - Manual trigger via GitHub UI

2. **Build the Docker image** using your Dockerfile

3. **Push to Docker Hub** with tags:
   - `latest` (for main branch)
   - `main` (branch name)
   - `v1.0.0`, `v1.0`, `v1` (for version tags)

4. **Update Docker Hub description** with your README.md

## Using the Published Image

Once the workflow runs successfully, anyone can pull and run:

```bash
# Pull the latest image
docker pull neeman2019/zoom2youtube:latest

# Run it
docker run -it --rm \
  -v $(pwd)/credentials:/app/credentials \
  -v $(pwd)/recordings:/app/recordings \
  -e ENV_FILE=/app/credentials/.env \
  neeman2019/zoom2youtube:latest
```

## Monitoring Builds

1. Go to **Actions** tab in your GitHub repository
2. You'll see the **Build and Push Docker Image** workflow
3. Click on any run to see detailed logs

## Creating Releases

To create a versioned release:

```bash
# Tag your release
git tag -a v1.0.0 -m "Release version 1.0.0"
git push origin v1.0.0
```

This will create Docker images with tags:
- `neeman2019/zoom2youtube:v1.0.0`
- `neeman2019/zoom2youtube:v1.0`
- `neeman2019/zoom2youtube:v1`
- `neeman2019/zoom2youtube:latest`

## Troubleshooting

### Build Fails with "unauthorized"
- Verify your Docker Hub secrets are correct
- Make sure the access token has Read, Write, Delete permissions

### Image not appearing on Docker Hub
- Check the Actions tab for error messages
- Verify your Docker Hub username is `neeman2019`
- Make sure the repository exists or set it to auto-create

### Want to change the Docker Hub username?
Edit `.github/workflows/docker-publish.yml` and change:
```yaml
env:
  DOCKER_IMAGE: neeman2019/zoom2youtube
```

## Security Notes

- Never commit Docker Hub credentials to the repository
- Access tokens can be revoked and regenerated if compromised
- GitHub Secrets are encrypted and only available to Actions
