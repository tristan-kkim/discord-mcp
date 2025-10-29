#!/bin/bash

# Discord MCP Server Wiki Deployment Script
# This script helps deploy Wiki pages to GitHub

echo "🚀 Discord MCP Server Wiki Deployment"
echo "======================================"

# Check if GitHub CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI not found. Please install it first."
    exit 1
fi

# Check if user is authenticated
if ! gh auth status &> /dev/null; then
    echo "❌ Not authenticated with GitHub. Please run 'gh auth login' first."
    exit 1
fi

echo "✅ GitHub CLI is ready"

# Check if Wiki is enabled
echo "🔍 Checking Wiki status..."
WIKI_STATUS=$(gh api repos/tristan-kkim/discord-mcp --jq '.has_wiki')

if [ "$WIKI_STATUS" = "false" ]; then
    echo "⚠️  Wiki is not enabled. Please enable it manually:"
    echo "   1. Go to https://github.com/tristan-kkim/discord-mcp"
    echo "   2. Click on 'Settings' tab"
    echo "   3. Scroll down to 'Features' section"
    echo "   4. Check 'Wikis' checkbox"
    echo "   5. Click 'Save'"
    echo ""
    echo "After enabling Wiki, run this script again."
    exit 1
fi

echo "✅ Wiki is enabled"

# Try to clone Wiki repository
echo "📥 Cloning Wiki repository..."
if git clone https://github.com/tristan-kkim/discord-mcp.wiki.git 2>/dev/null; then
    echo "✅ Wiki repository cloned successfully"
    cd discord-mcp.wiki
else
    echo "⚠️  Wiki repository not found. Creating first page manually..."
    echo "Please follow these steps:"
    echo "1. Go to https://github.com/tristan-kkim/discord-mcp/wiki"
    echo "2. Click 'Create the first page'"
    echo "3. Title: 'Home'"
    echo "4. Copy content from wiki/Home.md"
    echo "5. Click 'Create page'"
    echo ""
    echo "After creating the first page, run this script again."
    exit 1
fi

# Copy Wiki files
echo "📋 Copying Wiki files..."
cp ../wiki/*.md .

# Add and commit changes
echo "💾 Committing changes..."
git add .
git commit -m "Deploy comprehensive Wiki documentation

- Home page with navigation
- Installation Guide with step-by-step instructions  
- Quick Start guide for 5-minute setup
- Channel Tools reference with examples
- Security Guide with best practices
- API Endpoints complete reference
- Professional documentation structure"

# Push to GitHub
echo "🚀 Pushing to GitHub..."
git push origin main

echo "✅ Wiki deployment completed!"
echo ""
echo "📚 Your Wiki is now available at:"
echo "   https://github.com/tristan-kkim/discord-mcp/wiki"
echo ""
echo "📖 Wiki pages:"
echo "   - Home: https://github.com/tristan-kkim/discord-mcp/wiki/Home"
echo "   - Installation Guide: https://github.com/tristan-kkim/discord-mcp/wiki/Installation-Guide"
echo "   - Quick Start: https://github.com/tristan-kkim/discord-mcp/wiki/Quick-Start"
echo "   - Channel Tools: https://github.com/tristan-kkim/discord-mcp/wiki/Channel-Tools"
echo "   - Security Guide: https://github.com/tristan-kkim/discord-mcp/wiki/Security-Guide"
echo "   - API Endpoints: https://github.com/tristan-kkim/discord-mcp/wiki/API-Endpoints"
echo ""
echo "🎉 Wiki deployment successful!"
