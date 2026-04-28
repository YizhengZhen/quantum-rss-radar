#!/usr/bin/env python3
"""
Deploy built website to public repository.

This script pushes the built Jekyll site (_site directory) to a public
GitHub repository, keeping only the static website files.

Usage:
    python scripts/deploy_to_public_repo.py \
        --source-dir jekyll_site/_site \
        --public-repo-url https://github.com/YOUR_USERNAME/qfqe-new-papers.git \
        --branch main \
        --token $PUBLIC_REPO_TOKEN
"""

import os
import sys
import shutil
import tempfile
import subprocess
import argparse
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_command(cmd, cwd=None):
    """Run a shell command and return output."""
    logger.debug(f"Running command: {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd, capture_output=True, text=True
    )
    if result.returncode != 0:
        logger.error(f"Command failed: {cmd}")
        logger.error(f"Stdout: {result.stdout}")
        logger.error(f"Stderr: {result.stderr}")
        raise RuntimeError(f"Command failed with exit code {result.returncode}")
    return result.stdout


def deploy_to_public_repo(source_dir, public_repo_url, branch, token):
    """
    Deploy website files to public repository.
    
    Args:
        source_dir: Path to built website directory (_site)
        public_repo_url: URL of the public repository
        branch: Branch to push to (usually 'main' or 'gh-pages')
        token: GitHub token with push permissions
    """
    # Validate source directory
    source_path = Path(source_dir).resolve()
    if not source_path.exists():
        raise FileNotFoundError(f"Source directory not found: {source_path}")
    
    if not any(source_path.iterdir()):
        logger.warning(f"Source directory is empty: {source_path}")
        return False
    
    # Create temporary directory for cloning public repo
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Clone public repository with token authentication
        repo_url_with_token = public_repo_url.replace(
            "https://", f"https://x-access-token:{token}@"
        )
        
        logger.info(f"Cloning public repository: {public_repo_url}")
        run_command(f"git clone --depth 1 {repo_url_with_token} public_repo", cwd=temp_dir)
        
        repo_path = temp_path / "public_repo"
        
        # Configure git
        logger.info("Configuring git user")
        run_command("git config user.email 'github-actions@github.com'", cwd=repo_path)
        run_command("git config user.name 'GitHub Actions'", cwd=repo_path)
        
        # Switch to target branch or create it
        logger.info(f"Checking out branch: {branch}")
        try:
            run_command(f"git checkout {branch}", cwd=repo_path)
        except RuntimeError:
            # Branch doesn't exist, create it
            logger.info(f"Creating new branch: {branch}")
            run_command(f"git checkout -b {branch}", cwd=repo_path)
        
        # Remove all existing files (except .git directory)
        logger.info("Cleaning repository")
        for item in repo_path.iterdir():
            if item.name == ".git":
                continue
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        
        # Copy website files
        logger.info(f"Copying website files from {source_path}")
        for item in source_path.iterdir():
            dest = repo_path / item.name
            if item.is_dir():
                shutil.copytree(item, dest)
            else:
                shutil.copy2(item, dest)
        
        # Add .nojekyll file to disable Jekyll processing on GitHub Pages
        # This ensures static HTML files are served directly
        logger.info("Adding .nojekyll file")
        nojekyll_path = repo_path / ".nojekyll"
        nojekyll_path.touch()
        
        # Check if there are any changes
        status_output = run_command("git status --porcelain", cwd=repo_path).strip()
        if not status_output:
            logger.info("No changes to commit")
            return True
        
        # Commit and push
        logger.info("Committing changes")
        run_command("git add .", cwd=repo_path)
        commit_message = f"Update website: {os.environ.get('GITHUB_SHA', 'Automated deployment')}"
        run_command(f'git commit -m "{commit_message}"', cwd=repo_path)
        
        logger.info("Pushing to public repository")
        run_command(f"git push origin {branch}", cwd=repo_path)
        
        logger.info("Deployment completed successfully")
        return True


def main():
    parser = argparse.ArgumentParser(description="Deploy website to public repository")
    parser.add_argument(
        "--source-dir",
        default="jekyll_site/_site",
        help="Path to built website directory (default: jekyll_site/_site)"
    )
    parser.add_argument(
        "--public-repo-url",
        required=True,
        help="URL of the public GitHub repository"
    )
    parser.add_argument(
        "--branch",
        default="main",
        help="Branch to push to (default: main)"
    )
    parser.add_argument(
        "--token",
        required=True,
        help="GitHub token with push permissions"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Dry run - show what would be done without actually pushing"
    )
    
    args = parser.parse_args()
    
    # Validate source directory
    if not os.path.exists(args.source_dir):
        logger.error(f"Source directory does not exist: {args.source_dir}")
        sys.exit(1)
    
    # Check for website files
    website_files = list(Path(args.source_dir).iterdir())
    if not website_files:
        logger.error(f"No website files found in {args.source_dir}")
        sys.exit(1)
    
    logger.info(f"Source directory: {args.source_dir}")
    logger.info(f"Public repository: {args.public_repo_url}")
    logger.info(f"Branch: {args.branch}")
    logger.info(f"Number of website files: {len(website_files)}")
    
    if args.dry_run:
        logger.info("Dry run mode - no changes will be pushed")
        # List files that would be deployed
        for file_path in Path(args.source_dir).rglob("*"):
            if file_path.is_file():
                rel_path = file_path.relative_to(args.source_dir)
                logger.info(f"  Would deploy: {rel_path}")
        return
    
    # Perform deployment
    try:
        success = deploy_to_public_repo(
            source_dir=args.source_dir,
            public_repo_url=args.public_repo_url,
            branch=args.branch,
            token=args.token
        )
        if success:
            logger.info("✅ Deployment successful")
        else:
            logger.warning("⚠️ No changes were deployed")
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()