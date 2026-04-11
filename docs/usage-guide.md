# Usage Guide

This guide explains how to use immich-gpt for two main jobs:

- enriching metadata with AI
- organizing assets into albums or sub-albums with AI assistance

## What immich-gpt does

immich-gpt connects to your Immich library, syncs assets into its own review workflow, asks an AI model to classify and describe those assets, and lets you approve or edit the results before writing anything back to Immich.

Think of it as a review-first AI layer for your existing photo library.

## Core concepts

### Assets

Assets are the photos and videos synced from Immich into immich-gpt for analysis and review.

### Buckets

Buckets are the categories the AI uses to sort your assets. A bucket can represent things like:

- Family
- Travel
- Receipts
- Work
- Screenshots
- Trash

Each bucket has its own prompt and behavior.

### Mapping modes

Each bucket has a mapping mode that controls what happens after approval:

- **Virtual**: keep the classification inside immich-gpt only
- **Immich Album**: add the approved asset to a specific existing Immich album
- **Parent Group**: place the approved asset into a bucket-based album group and use the AI suggestion or your edit as the sub-album name
- **Immich Trash**: move the approved asset to the Immich trash

### Review queue

The review queue is where AI suggestions are checked before write-back. You can:

- approve a suggestion as-is
- edit the bucket, description, tags, or album name
- reject the suggestion
- re-run AI analysis on an asset

## Before you start

You will typically need:

- an existing Immich server
- an Immich API key
- at least one AI provider configured, such as OpenAI, OpenRouter, or Ollama

## Recommended first-time setup

### 1. Complete the initial login/setup flow

On first launch, create the initial admin account and sign in.

### 2. Connect your Immich server

Go to **Settings** and enter your:

- Immich URL
- Immich API key

Once saved, immich-gpt can read your library and fetch album lists for mapping.

### 3. Configure an AI provider

In **Settings**, configure the provider you want to use:

- **OpenAI** for hosted models
- **OpenRouter** for wider hosted model choice
- **Ollama** for local models

Choose the model you want the app to use for classification and metadata suggestions.

### 4. Set AI behavior rules

In **Settings**, decide whether the AI should:

- create new tag names, or only work with existing asset tags
- suggest new album names, or only use albums that already exist in Immich

These settings are useful if you want tighter control over write-back behavior.

### 5. Create and tune your buckets

Go to **Buckets** and create categories that match how you want your library organized.

For each bucket, define:

- a name
- an optional description
- a classification prompt
- a priority
- a mapping mode
- an optional minimum confidence threshold

#### Example bucket ideas

- **Family** -> Parent Group
- **Travel** -> Parent Group
- **Receipts** -> Virtual
- **Favourites Archive** -> Immich Album
- **Trash** -> Immich Trash

## Main workflow: metadata enrichment

Use this workflow when your main goal is better descriptions and tags.

### Step 1. Sync assets from Immich

From the dashboard, choose one of these scopes:

- **All Photos & Videos**
- **Favourites Only**
- **Specific Albums**

Then choose a workflow mode:

- **Sync Only**
- **Sync + AI**
- **AI Only**

For a first run, **Sync + AI** is usually the easiest option.

### Step 2. Let the AI classify assets

The AI will analyze each synced asset and suggest:

- the best matching bucket
- a description
- tags
- an album or sub-album suggestion when relevant

### Step 3. Open the review queue

Go to **Review** to inspect the pending suggestions.

For each asset, you can:

- change the bucket
- rewrite the description
- add or remove tags
- accept or change the album/sub-album
- approve or reject the result

### Step 4. Approve write-back

When you approve an item, immich-gpt writes the approved result back according to the selected bucket mode.

For metadata-focused setups, many users start with:

- **Virtual** for experimentation
- **Immich Album** or **Parent Group** once they trust the prompts and bucket rules

## Main workflow: AI-assisted album creation and organization

Use this workflow when your main goal is to sort assets into better album structures.

### Option A: Map a bucket to an existing Immich album

Choose **Immich Album** as the bucket mapping mode when you want all approved assets in that bucket to go into a specific album that already exists in Immich.

Good examples:

- a bucket named **Family Highlights** mapped to an existing `Family Highlights` album
- a bucket named **Portfolio** mapped to an existing `Portfolio` album

### Option B: Use Parent Group for AI-suggested sub-albums

Choose **Parent Group** when you want a bucket to act like a higher-level category and let the AI suggest the lower-level album name.

Examples:

- bucket: **Travel** -> sub-albums like `Paris`, `Tokyo`, `Iceland`
- bucket: **Events** -> sub-albums like `Birthday Party`, `Wedding`, `School Play`

This is the most flexible option if you want AI to help create a cleaner album structure over time.

### Option C: Restrict album suggestions to existing albums only

If you want tighter control, set album behavior to **Only use existing albums** in **Settings**.

This is useful when:

- your album naming is already standardized
- you want review suggestions to stay inside your current album system
- you do not want the AI inventing new album names

### Review before write-back

Even in album-focused workflows, the review queue stays important. Before approval, you can:

- keep the suggested album/sub-album
- replace it with an existing album
- type a different name manually
- change the bucket entirely if the classification is wrong

## Suggested rollout strategy

If you are using the app for the first time, a safe rollout looks like this:

1. Start with a few carefully written buckets
2. Run on **Specific Albums** or **Favourites Only**
3. Review a sample of results closely
4. Adjust prompts, priorities, and confidence thresholds
5. Expand to more albums or your full library

This gives you a chance to improve the prompts before applying the workflow at scale.

## Tips for better results

### Write narrow bucket prompts

Specific prompts usually produce better results than broad ones. Instead of:

- "travel photos"

try:

- "holiday and travel photos showing landmarks, landscapes, hotels, airports, or sightseeing scenes; exclude family portraits taken at home"

### Use priority to resolve overlap

If two buckets could both match the same asset, give the more important or more specific bucket a higher priority by using a lower number.

### Use confidence thresholds carefully

If you only want strong suggestions to appear, set a minimum confidence. If you want to inspect more borderline cases, leave it empty and review everything.

### Start virtual when experimenting

If you are unsure about a bucket, use **Virtual** first. That lets you test the classification logic without changing albums in Immich.

## Common usage patterns

### Metadata-first setup

Use mostly **Virtual** buckets and focus on improving descriptions and tags for searchability.

### Album-organization setup

Use **Immich Album** and **Parent Group** buckets to turn AI classification into album placement.

### Clean-up setup

Use an **Immich Trash** bucket for low-value assets you want to review for deletion in Immich.

## After approval: what gets written back

Depending on the bucket and your edits, approval can write back:

- updated descriptions
- approved tags
- album placement
- sub-album placement
- trash moves for clean-up buckets

Nothing is written back until you approve it.

## Good places to document this later

When you are ready to include this in public-facing documentation, this guide fits well as:

- a `docs/usage-guide.md` page linked from the README
- a "How it works" section on the GitHub front page
- a longer "Getting started" or "Usage" page for future project docs
