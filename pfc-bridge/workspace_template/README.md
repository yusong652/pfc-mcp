# PFC Workspace Template

This directory contains template files for initializing a new PFC project workspace.

## Usage

Copy the `.gitignore` file to your PFC project workspace:

```bash
# From your PFC workspace directory
cp /path/to/pfc-mcp/pfc-bridge/workspace_template/.gitignore .
```

Or manually create it with the contents from this template.

## What's Included

- `.gitignore` - Ignores PFC runtime files, logs, and temporary files

## Recommended Workflow

1. Create your PFC project directory
2. Copy the `.gitignore` template
3. Initialize git: `git init`
4. Add your initial files: `git add .`
5. Create initial commit: `git commit -m "Initial PFC project setup"`

Now you're ready to use the PFC tools with proper version tracking!
