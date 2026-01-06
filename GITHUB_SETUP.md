# GitHub Repository Setup Guide

Your repository is ready to be pushed to GitHub! Follow these steps:

## Step 1: Create a New Repository on GitHub

1. Go to [GitHub](https://github.com) and sign in
2. Click the **"+"** icon in the top right corner
3. Select **"New repository"**
4. Fill in the repository details:
   - **Repository name**: `fantasyFootball` (or your preferred name)
   - **Description**: "Automated fantasy football lineup optimizer for Yahoo Fantasy Sports"
   - **Visibility**: Choose Public or Private
   - **DO NOT** initialize with README, .gitignore, or license (we already have these)
5. Click **"Create repository"**

## Step 2: Push Your Code to GitHub

After creating the repository, GitHub will show you commands. Use these commands in your terminal:

```bash
cd /Users/ramgoli/fantasyFootball

# Add the remote repository (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/fantasyFootball.git

# Rename branch to main (if not already)
git branch -M main

# Push your code
git push -u origin main
```

**Alternative: Using SSH (if you have SSH keys set up)**
```bash
git remote add origin git@github.com:YOUR_USERNAME/fantasyFootball.git
git push -u origin main
```

## Step 3: Verify Everything is Pushed

1. Go to your repository on GitHub
2. Verify all files are there
3. Check that sensitive files are NOT visible:
   - ✅ `config.yaml.example` should be visible (template)
   - ❌ `config.yaml` should NOT be visible (your actual config)
   - ❌ `tokens.json` should NOT be visible
   - ❌ `oauth2.json` should NOT be visible
   - ❌ `fantasy_bot.db` should NOT be visible

## Step 4: Add Repository Description and Topics

On your GitHub repository page:
1. Click the gear icon ⚙️ next to "About"
2. Add a description: "Automated fantasy football lineup optimizer using betting data, projections, and matchups"
3. Add topics: `fantasy-football`, `yahoo-fantasy`, `python`, `automation`, `betting-data`, `lineup-optimizer`

## Step 5: (Optional) Set Up GitHub Actions

If you want to use GitHub Actions for automated runs, you'll need to:
1. Go to Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `YAHOO_CLIENT_ID`: Your Yahoo client ID
   - `YAHOO_CLIENT_SECRET`: Your Yahoo client secret
   - `LEAGUE_ID`: Your league ID
   - `TEAM_ID`: Your team ID
   - `ODDS_API_KEY`: (Optional) Your Odds API key

## Troubleshooting

### Authentication Issues
If you get authentication errors:
- Use a Personal Access Token instead of password
- Or set up SSH keys: https://docs.github.com/en/authentication/connecting-to-github-with-ssh

### Branch Name Issues
If you get branch name errors:
```bash
git branch -M main
git push -u origin main
```

### Remote Already Exists
If you get "remote origin already exists":
```bash
git remote remove origin
git remote add origin https://github.com/YOUR_USERNAME/fantasyFootball.git
```

## Next Steps

After pushing to GitHub:
1. Share the repository with others
2. Consider adding a GitHub Pages site for documentation
3. Add issues/feature requests
4. Accept contributions via pull requests

---

**Your repository is ready! 🚀**

